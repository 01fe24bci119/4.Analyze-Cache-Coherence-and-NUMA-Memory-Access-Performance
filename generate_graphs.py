import os
import matplotlib.pyplot as plt
import numpy as np

os.environ['MPLCONFIGDIR'] = os.path.abspath('./.mplconfig')
os.makedirs('./.mplconfig', exist_ok=True)
os.makedirs('./graphs', exist_ok=True)

plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
plt.rcParams.update({
    'font.sans-serif': 'DejaVu Sans',
    'font.family': 'sans-serif',
    'figure.autolayout': True,
    'axes.titlesize': 14,
    'axes.labelsize': 12,
    'xtick.labelsize': 11,
    'ytick.labelsize': 11,
})

# -------------------------------------------------------------
# Graph 1: False Sharing Impact on Execution Time
# -------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8, 5), dpi=300)
threads = ['1 Thread', '2 Threads', '4 Threads']
x = np.arange(len(threads))
width = 0.35

# Data from Table 1 (compare_numa default run)
adjacent_times = [0.0233, 0.0142, 0.0065]
padded_times   = [0.0220, 0.0111, 0.0058]

rects1 = ax.bar(x - width/2, adjacent_times, width, label='Adjacent (False Sharing)', color='#e74c3c', edgecolor='black', alpha=0.9)
rects2 = ax.bar(x + width/2, padded_times, width, label='Padded (64-byte Aligned)', color='#2ecc71', edgecolor='black', alpha=0.9)

ax.set_ylabel('Execution Time (seconds)')
ax.set_title('False Sharing: Adjacent vs. Padded Counter Layout (100M Increments)')
ax.set_xticks(x)
ax.set_xticklabels(threads)
ax.legend(frameon=True)
ax.set_ylim(0, 0.028)

for rect in rects1:
    h = rect.get_height()
    ax.annotate(f'{h:.4f}s', xy=(rect.get_x() + rect.get_width() / 2, h),
                xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=9, fontweight='bold')
for rect in rects2:
    h = rect.get_height()
    ax.annotate(f'{h:.4f}s', xy=(rect.get_x() + rect.get_width() / 2, h),
                xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=9, fontweight='bold')

plt.tight_layout()
plt.savefig('./graphs/false_sharing_execution_time.png')
plt.close()

# -------------------------------------------------------------
# Graph 2: Coherence Protocol Performance Comparison (Bus Traffic)
# -------------------------------------------------------------
fig, ax = plt.subplots(figsize=(9, 5), dpi=300)
metrics = ['Bus Transactions', 'Invalidations', 'Write-backs to RAM', 'Cache-to-Cache (C2C)']
x = np.arange(len(metrics))
width = 0.25

# 1000 iterations adjacent layout
msi_vals   = [4000, 1999, 1999, 0]
mesi_vals  = [3999, 1999, 1999, 0]
moesi_vals = [3999, 1999, 0, 1999]

r1 = ax.bar(x - width, msi_vals, width, label='MSI', color='#3498db', edgecolor='black')
r2 = ax.bar(x, mesi_vals, width, label='MESI', color='#9b59b6', edgecolor='black')
r3 = ax.bar(x + width, moesi_vals, width, label='MOESI', color='#f39c12', edgecolor='black')

ax.set_ylabel('Total Count (1000 Iterations / 4000 Ops)')
ax.set_title('Cache Coherence Protocol Metrics (Adjacent Layout)')
ax.set_xticks(x)
ax.set_xticklabels(metrics)
ax.legend(frameon=True)
ax.set_ylim(0, 4800)

for r in [r1, r2, r3]:
    for rect in r:
        h = rect.get_height()
        if h > 0:
            ax.annotate(f'{int(h)}', xy=(rect.get_x() + rect.get_width() / 2, h),
                        xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=8)

plt.tight_layout()
plt.savefig('./graphs/coherence_protocols_traffic.png')
plt.close()

# -------------------------------------------------------------
# Graph 3: NUMA Memory Sweep Execution Time
# -------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8, 5), dpi=300)
threads = ['1 Thread', '2 Threads']
x = np.arange(len(threads))
width = 0.25

# Data from Table 2 sweeps (512 MB buffer, 4 passes)
default_times = [0.1178, 0.1061]
local_times   = [0.1138, 0.1036]
remote_times  = [0.1137, 0.1101]

r1 = ax.bar(x - width, default_times, width, label='Default (No Binding)', color='#7f8c8d', edgecolor='black')
r2 = ax.bar(x, local_times, width, label='Local (Node 0 Mem)', color='#2980b9', edgecolor='black')
r3 = ax.bar(x + width, remote_times, width, label='Remote (Node 1 Mem)', color='#d35400', edgecolor='black')

ax.set_ylabel('Execution Time (seconds)')
ax.set_title('NUMA 512MB Buffer Sweep: Local vs Remote Memory Placement')
ax.set_xticks(x)
ax.set_xticklabels(threads)
ax.legend(frameon=True)
ax.set_ylim(0, 0.14)

for r in [r1, r2, r3]:
    for rect in r:
        h = rect.get_height()
        ax.annotate(f'{h:.4f}s', xy=(rect.get_x() + rect.get_width() / 2, h),
                    xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=8, fontweight='bold')

plt.tight_layout()
plt.savefig('./graphs/numa_memory_latency.png')
plt.close()

print('Graphs generated successfully!')
