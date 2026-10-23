import pandas as pd, json, os

# Load metric TSV for checkout service
metric_file = os.path.join('metrics', 'service_checkout_raw.tsv')
df = pd.read_csv(metric_file, sep='\t')
# Filter for duration metric and bucket >= 1500ms
duration = df[df['metric_name'].str.contains('traces_span_metrics_duration_milliseconds_bucket')]
# Compute approximate 95th percentile using bucket counts
# Here we approximate by taking the highest bucket with non-zero count
high = duration[duration['le'].astype(float) >= 1500]
print('Rows with le >=1500ms:', len(high))
# Summarize counts per bucket
print(high.groupby('le')['value'].sum().sort_index())
