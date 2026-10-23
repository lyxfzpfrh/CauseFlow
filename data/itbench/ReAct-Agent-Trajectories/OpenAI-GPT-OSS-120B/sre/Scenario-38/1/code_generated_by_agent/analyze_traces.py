#!/usr/bin/env python3

"""Simple analysis of OTEL traces to find error spans for checkout service during incident."""

import pathlib, csv, collections

trace_file = pathlib.Path("/root/projects/open_source/zero/B96DF826-4BB2-4B62-97AB-6D84254C53D7/Scenario-38/otel_traces.tsv")

def main():
    error_counts = collections.Counter()
    total_counts = collections.Counter()
    with trace_file.open() as f:
        reader = csv.DictReader(f, delimiter='\t')
        for r in reader:
            if r.get('service_name') != 'checkout':
                continue
            total_counts['checkout'] += 1
            if r.get('status_code') and r['status_code'] != 'OK':
                error_counts['checkout'] += 1
    if total_counts['checkout'] == 0:
        print('No checkout spans')
        return
    err_rate = error_counts['checkout'] / total_counts['checkout'] * 100
    print(f"checkout spans: {total_counts['checkout']}, error spans: {error_counts['checkout']}, error_rate=%{err_rate:.2f}")

if __name__ == '__main__':
    main()

