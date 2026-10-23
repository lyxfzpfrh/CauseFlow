"""Trajectory loaders for the two benchmarks.

CodeTraceBench (RQ1/RQ3/RQ4)
    The verified split ships a *manifest* (1,000 rows, included here as
    ``data/codetracebench/manifest_verified.parquet``);
    ``prepare_eval_split.py`` derives the 235-trajectory evaluation set from
    the manifest alone.  The per-trajectory raw runs are shipped as
    ``data/codetracebench/artifacts/<traj_id>.tar.zst``;
    ``load_codetracebench_archive`` reads a trajectory directly from the
    archive (mini-swe-agent traj.json, terminus2 episode logs).

ITBench (RQ2)
    ``data/itbench/ReAct-Agent-Trajectories/`` holds the 35 SRE scenarios x
    3 runs of the official ITBench-SRE-Agent on GPT-OSS-120B (105 runs);
    ``data/itbench/label_runs.py`` derives ``itbench_runs_manifest.parquet``
    with the per-run verdict.  ``load_itbench_session`` parses the
    session.jsonl agent traces; ``load_react_log`` parses the per-episode
    prompt/response layout.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional

from .schema import EditableInput, EditableKind, Step, Trajectory


# --------------------------------------------------------------------------
# CodeTraceBench manifest
# --------------------------------------------------------------------------
def load_manifest(path) -> "pandas.DataFrame":
    import pandas as pd
    return pd.read_parquet(path)


def _first_incorrect(row) -> Optional[int]:
    """i*: the earliest annotated incorrect step of a failed trajectory."""
    stages = row.get("incorrect_stages")
    if stages is None or len(stages) == 0:
        return None
    ids = []
    for st in stages:
        raw = st.get("incorrect_step_ids")
        if raw is None:
            continue
        arr = list(raw) if not hasattr(raw, "tolist") else raw.tolist()
        ids.extend(int(x) for x in arr)
    return min(ids) if ids else None


def build_eval_split(manifest) -> "pandas.DataFrame":
    """The 235-trajectory evaluation set of RQ1 / RQ3 / RQ4.

    Failed trajectories (verdict != solved, including null verdicts) with a
    non-empty step-level incorrect-step annotation: 69 SWE-bench + 166
    Terminal-Bench = 235, each carrying exactly one annotated root-cause
    step used as i* (§4.1.1, three-reason identification).
    """
    df = manifest
    failed = df[df["solved"] != True].copy()          # noqa: E712
    failed["i_star"] = failed.apply(_first_incorrect, axis=1)
    annot = failed[failed["i_star"].notna()].copy()
    annot["i_star"] = annot["i_star"].astype(int)
    annot["src"] = annot["source_relpath"].str.split("/").str[0]
    annot["src_bench"] = annot["src"].map(
        lambda s: "SWE-bench" if s == "swe_raw" else "Terminal-Bench")
    annot["length_band"] = annot["step_count"].map(
        lambda n: "short (<=30)" if n <= 30 else
                  ("medium (31-80)" if n <= 80 else "long (>80)"))
    return annot.reset_index(drop=True)


# --------------------------------------------------------------------------
# Generic ReAct agent-log loader (episode dirs with prompt/response pairs)
# --------------------------------------------------------------------------
_SYS_BLOCK = re.compile(r"<system_prompt>(.*?)</system_prompt>", re.S)
_INSTR_BLOCK = re.compile(r"<task_instruction>(.*?)</task_instruction>", re.S)


def _extract_blocks(prompt: str) -> Dict[str, str]:
    segs: Dict[str, str] = {}
    m = _SYS_BLOCK.search(prompt)
    if m:
        segs["system"] = m.group(1).strip()
    m = _INSTR_BLOCK.search(prompt)
    if m:
        segs["instruction"] = m.group(1).strip()
    return segs


def load_react_log(root: str or Path, traj_id: str = "") -> Trajectory:
    """Load a per-episode prompt/response agent log directory.

    Each ``episode-*/`` subdirectory holds ``prompt.txt`` (the step input)
    and ``response.txt`` (the step output).  The environment feedback of
    step i is approximated by the new content that appears in prompt i+1
    (the observation the environment appended), which is how ReAct-style
    logs accumulate context.
    """
    root = Path(root)
    episodes = sorted([d for d in root.rglob("episode-*") if d.is_dir()],
                      key=lambda d: d.name)
    steps: List[Step] = []
    editable: Dict[str, EditableInput] = {}
    for i, ep in enumerate(episodes):
        prompt_f, resp_f = ep / "prompt.txt", ep / "response.txt"
        if not prompt_f.exists() or not resp_f.exists():
            continue
        prompt = prompt_f.read_text(encoding="utf-8", errors="replace")
        response = resp_f.read_text(encoding="utf-8", errors="replace")
        segs = _extract_blocks(prompt)
        if "system" in segs and "system" not in editable:
            editable["system"] = EditableInput(
                EditableKind.SYSTEM_PROMPT, segs["system"], "system prompt")
        if "instruction" in segs and "instruction" not in editable:
            editable["instruction"] = EditableInput(
                EditableKind.TASK_INSTRUCTION, segs["instruction"],
                "task instruction")
        # observation = new content in this prompt vs the previous one
        obs = ""
        if i > 0:
            prev = (episodes[i - 1] / "prompt.txt").read_text(
                encoding="utf-8", errors="replace")
            if prompt.startswith(prev):
                obs = prompt[len(prev):].strip()
        steps.append(Step(index=len(steps) + 1, input_text=prompt,
                          output_text=response, observation=obs,
                          segments=segs))
    return Trajectory(traj_id=traj_id or root.name, steps=steps,
                      editable_inputs=list(editable.values()), verdict="fail")


def load_tensorblock_log(json_path: str or Path,
                         traj_id: str = "") -> Trajectory:
    """Load a TensorBlock-style agent-run JSON (list of messages/turns)."""
    data = json.loads(Path(json_path).read_text(encoding="utf-8",
                                                errors="replace"))
    steps: List[Step] = []
    editable: List[EditableInput] = []
    turns = data if isinstance(data, list) else data.get("messages", [])
    for t in turns:
        role = t.get("role", "")
        content = t.get("content", "")
        if role == "system" and not any(
                e.kind == EditableKind.SYSTEM_PROMPT for e in editable):
            editable.append(EditableInput(EditableKind.SYSTEM_PROMPT, content,
                                          "system prompt"))
            continue
        if role == "user" and not any(
                e.kind == EditableKind.TASK_INSTRUCTION for e in editable) \
                and not steps:
            editable.append(EditableInput(EditableKind.TASK_INSTRUCTION,
                                          content, "task instruction"))
            continue
        if role == "assistant":
            steps.append(Step(index=len(steps) + 1, input_text="",
                              output_text=content))
        elif role == "user" and steps:
            steps[-1].observation = content
    return Trajectory(traj_id=traj_id or Path(json_path).stem, steps=steps,
                      editable_inputs=editable, verdict="fail")


# --------------------------------------------------------------------------
# ITBench session.jsonl (OpenAI Agents SDK trace)
# --------------------------------------------------------------------------
def load_itbench_session(jsonl_path: str or Path,
                         traj_id: str = "") -> Trajectory:
    """Load an ITBench agent-run ``session.jsonl`` (RQ2 trajectories).

    The trace is an OpenAI Agents SDK session log: one JSON object per line
    with ``type`` in {session_meta, response_item, event_msg, turn_context}.
    Conversation turns come from ``response_item`` events of type
    ``message`` (role user/assistant); tool calls appear as function_call /
    function_call_output items, folded into the step's action/observation.
    The first user message carries the task instructions (including the
    AGENTS.md system context), which become the editable inputs.
    """
    path = Path(jsonl_path)
    steps: List[Step] = []
    editable: List[EditableInput] = []
    first_user_done = False

    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            if ev.get("type") != "response_item":
                continue
            item = ev.get("payload", {})
            itype = item.get("type")
            if itype == "message":
                role = item.get("role", "")
                text = " ".join(
                    p.get("text", "") for p in item.get("content", [])
                    if isinstance(p, dict))
                if role == "user" and not first_user_done:
                    first_user_done = True
                    editable.append(EditableInput(
                        EditableKind.TASK_INSTRUCTION, text,
                        "task instruction"))
                elif role == "assistant":
                    steps.append(Step(index=len(steps) + 1,
                                      input_text="", output_text=text))
                elif role == "user" and steps:
                    steps[-1].observation = text
            elif itype == "function_call":
                name = item.get("name", "tool")
                args = str(item.get("arguments", ""))[:200]
                if steps:
                    steps[-1].output_text += f"\n[{name}({args})]"
                else:
                    steps.append(Step(index=1, input_text="",
                                      output_text=f"[{name}({args})]"))
            elif itype == "function_call_output":
                out = str(item.get("output", ""))[:400]
                if steps:
                    steps[-1].observation += ("\n" + out).strip()

    if not editable:
        editable.append(EditableInput(EditableKind.TASK_INSTRUCTION,
                                      "(task instruction not recorded)",
                                      "task instruction"))
    return Trajectory(traj_id=traj_id or path.parent.name, steps=steps,
                      editable_inputs=editable, verdict="fail")


# --------------------------------------------------------------------------
# CodeTraceBench per-trajectory archive (tar.zst, shipped in data/)
# --------------------------------------------------------------------------
def load_codetracebench_archive(archive_path: str or Path,
                                traj_id: str = "") -> Trajectory:
    """Load a trajectory directly from a ``<traj_id>.tar.zst`` archive.

    Supports the two archive layouts of the verified split:
      * mini-swe-agent: ``agent-logs/mini.traj.json`` with a ``messages``
        list (role system/user/assistant, one exchange per step);
      * terminus2: ``agent-logs/episode-*/`` prompt.txt / response.txt
        (delegates to ``load_react_log`` over the extracted episode dirs).

    Requires the ``zstandard`` package.  Returns a Trajectory with
    verdict='fail' (archives are shipped only for the failed evaluation
    set).
    """
    import io
    import tarfile

    import zstandard as zstd

    path = Path(archive_path)
    traj_id = traj_id or path.name[:-len(".tar.zst")]

    with open(path, "rb") as fh:
        dctx = zstd.ZstdDecompressor()
        with dctx.stream_reader(fh) as reader:
            with tarfile.open(fileobj=io.BytesIO(reader.read())) as tar:
                names = tar.getnames()

                # mini-swe-agent / openhands message-list trajectory
                traj_json = next(
                    (n for n in names
                     if n.endswith(".traj.json") or n.endswith("traj.json")),
                    None)
                if traj_json is not None:
                    data = json.load(tar.extractfile(traj_json))
                    msgs = data.get("messages", data) if isinstance(
                        data, dict) else data
                    steps: List[Step] = []
                    editable: List[EditableInput] = []
                    for m in msgs:
                        role = m.get("role", "")
                        content = m.get("content", "")
                        if isinstance(content, list):
                            content = " ".join(
                                p.get("text", "") for p in content
                                if isinstance(p, dict))
                        if role == "system" and not any(
                                e.kind == EditableKind.SYSTEM_PROMPT
                                for e in editable):
                            editable.append(EditableInput(
                                EditableKind.SYSTEM_PROMPT, content,
                                "system prompt"))
                        elif role == "user" and not steps and not any(
                                e.kind == EditableKind.TASK_INSTRUCTION
                                for e in editable):
                            editable.append(EditableInput(
                                EditableKind.TASK_INSTRUCTION, content,
                                "task instruction"))
                        elif role == "assistant":
                            steps.append(Step(index=len(steps) + 1,
                                              input_text="",
                                              output_text=content))
                        elif role == "user" and steps:
                            steps[-1].observation = content
                    if steps:
                        return Trajectory(traj_id=traj_id, steps=steps,
                                          editable_inputs=editable,
                                          verdict="fail")

                # openhands SWE-bench layout: timestamped per-call JSONs,
                # each {messages: [...input so far...], response: <output>}
                call_jsons = sorted(
                    (n for n in names if n.endswith(".json")
                     and not n.endswith(("checkpoints.jsonl",))
                     and "/sessions/" not in n and "results" not in n
                     and "metrics" not in n and "report" not in n
                     and not n.endswith("traj.json")),
                    key=lambda n: n)
                if call_jsons and len(call_jsons) >= 2:
                    last = None
                    for cand in reversed(call_jsons):
                        try:
                            j = json.load(tar.extractfile(cand))
                        except json.JSONDecodeError:
                            continue
                        if isinstance(j, dict) and "messages" in j:
                            last = j
                            break
                    if last is not None:
                        msgs = list(last["messages"])
                        resp = last.get("response")
                        if isinstance(resp, dict):
                            resp = resp.get("content", resp)
                        if isinstance(resp, list):
                            resp = " ".join(
                                p.get("text", "") for p in resp
                                if isinstance(p, dict))
                        steps: List[Step] = []
                        editable: List[EditableInput] = []
                        for m in msgs:
                            role = m.get("role", "")
                            content = m.get("content", "")
                            if isinstance(content, list):
                                content = " ".join(
                                    p.get("text", "") for p in content
                                    if isinstance(p, dict))
                            if role == "system" and not any(
                                    e.kind == EditableKind.SYSTEM_PROMPT
                                    for e in editable):
                                editable.append(EditableInput(
                                    EditableKind.SYSTEM_PROMPT, content,
                                    "system prompt"))
                            elif role == "user" and not steps and not any(
                                    e.kind == EditableKind.TASK_INSTRUCTION
                                    for e in editable):
                                editable.append(EditableInput(
                                    EditableKind.TASK_INSTRUCTION, content,
                                    "task instruction"))
                            elif role == "assistant":
                                steps.append(Step(index=len(steps) + 1,
                                                  input_text="",
                                                  output_text=content))
                            elif role == "user" and steps:
                                steps[-1].observation = content
                        if resp:
                            steps.append(Step(index=len(steps) + 1,
                                              input_text="",
                                              output_text=str(resp)))
                        if steps:
                            return Trajectory(traj_id=traj_id, steps=steps,
                                              editable_inputs=editable,
                                              verdict="fail")

                # openhands: sessions/<uuid>.json event list, or per-event
                # files under sessions/**/events/<id>.json
                sess_json = next(
                    (n for n in names if "/sessions/" in n
                     and n.endswith(".json") and "event_cache" not in n
                     and "/events/" not in n),
                    None)
                events = None
                if sess_json is not None:
                    loaded = json.load(tar.extractfile(sess_json))
                    if isinstance(loaded, list) and all(
                            isinstance(e, dict) for e in loaded):
                        events = loaded
                else:
                    ev_files = [n for n in names if "/events/" in n
                                and n.endswith(".json")]
                    if ev_files:
                        def _ev_key(n):
                            stem = n.split("/")[-1].split(".")[0]
                            return int(stem) if stem.isdigit() else 0
                        events = []
                        for n in sorted(ev_files, key=_ev_key):
                            try:
                                ev = json.load(tar.extractfile(n))
                            except json.JSONDecodeError:
                                continue
                            if isinstance(ev, dict):
                                events.append(ev)
                if events:
                    steps: List[Step] = []
                    editable: List[EditableInput] = []
                    for ev in events:
                            src = ev.get("source")
                            action = ev.get("action")
                            msg = str(ev.get("message", ""))
                            if src == "agent" and action == "system" and not any(
                                    e.kind == EditableKind.SYSTEM_PROMPT
                                    for e in editable):
                                editable.append(EditableInput(
                                    EditableKind.SYSTEM_PROMPT, msg,
                                    "system prompt"))
                            elif src == "user" and action == "message" \
                                    and not any(
                                        e.kind == EditableKind.TASK_INSTRUCTION
                                        for e in editable):
                                editable.append(EditableInput(
                                    EditableKind.TASK_INSTRUCTION, msg,
                                    "task instruction"))
                            elif src == "agent" and action is not None:
                                args = ev.get("args") or {}
                                if isinstance(args, dict):
                                    cmd = args.get("command",
                                                   args.get("content", ""))
                                    thought = args.get("thought", "")
                                else:
                                    cmd, thought = str(args), ""
                                out = (thought + "\n" + str(cmd)).strip()
                                steps.append(Step(index=len(steps) + 1,
                                                  input_text="",
                                                  output_text=out))
                            elif steps and src in ("agent", "environment"):
                                # observation event following the last action
                                steps[-1].observation = \
                                    (steps[-1].observation + "\n" + msg).strip()
                    if steps:
                            return Trajectory(traj_id=traj_id, steps=steps,
                                              editable_inputs=editable,
                                              verdict="fail")

                # swe-agent: <instance>.traj (JSON with a trajectory list)
                traj_member = next(
                    (n for n in names if n.endswith(".traj")), None)
                if traj_member is not None:
                    data = json.load(tar.extractfile(traj_member))
                    entries = data.get("trajectory", data) if isinstance(
                        data, dict) else data
                    steps: List[Step] = []
                    for ev in entries:
                        if not isinstance(ev, dict):
                            continue
                        steps.append(Step(
                            index=len(steps) + 1,
                            input_text="",
                            output_text=str(ev.get("action", "")),
                            observation=str(ev.get("observation", ""))))
                    if steps:
                        editable = [EditableInput(
                            EditableKind.TASK_INSTRUCTION,
                            path.stem.rsplit(".", 1)[0]
                            if "." in path.stem else path.stem,
                            "task instruction")]
                        return Trajectory(traj_id=traj_id, steps=steps,
                                          editable_inputs=editable,
                                          verdict="fail")

                # swe-agent: <instance>.checkpoints.jsonl
                ckpt = next(
                    (n for n in names if n.endswith("checkpoints.jsonl")),
                    None)
                if ckpt is not None:
                    lines = tar.extractfile(ckpt).read().decode(
                        "utf-8").splitlines()
                    steps: List[Step] = []
                    for line in lines:
                        try:
                            ev = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        steps.append(Step(
                            index=len(steps) + 1,
                            input_text="",
                            output_text=str(ev.get("action", "")),
                            observation=str(ev.get("observation", ""))))
                    if steps:
                        editable = [EditableInput(
                            EditableKind.TASK_INSTRUCTION,
                            path.stem.rsplit(".", 1)[0]
                            if "." in path.stem else path.stem,
                            "task instruction")]
                        return Trajectory(traj_id=traj_id, steps=steps,
                                          editable_inputs=editable,
                                          verdict="fail")

                # terminus2 episode logs: extract to a scratch directory and
                # reuse the ReAct loader (it rglobs episode-* dirs)
                episode_members = [n for n in names if "/episode-" in n]
                if episode_members:
                    import tempfile
                    with tempfile.TemporaryDirectory() as tmp:
                        for member in tar.getmembers():
                            if not member.isfile():
                                continue
                            rel = member.name.split("/", 1)[-1] if "/" \
                                in member.name else member.name
                            dest = Path(tmp) / rel.replace("/", os.sep)
                            dest.parent.mkdir(parents=True, exist_ok=True)
                            with open(dest, "wb") as out:
                                out.write(tar.extractfile(member).read())
                        return load_react_log(Path(tmp), traj_id=traj_id)

    raise ValueError(f"no recognizable trajectory in {archive_path}")
