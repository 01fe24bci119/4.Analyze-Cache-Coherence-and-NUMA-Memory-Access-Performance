# Analyze Cache Coherence (MSI, MESI, MOESI) and NUMA Memory Access Performance

A comprehensive experimental study analyzing **Hardware Cache Coherence Protocols (MSI, MESI, MOESI)**, **False Sharing phenomena**, and **Non-Uniform Memory Access (NUMA) memory placement latencies** in modern multi-core computing architectures.

---

## Table of Contents
1. [Experiment Overview & Objective](#1-experiment-overview--objective)
2. [Theoretical Background](#2-theoretical-background)
   - [Why Cache Coherence is Needed](#21-why-cache-coherence-is-needed)
   - [Cache Line Granularity & False Sharing](#22-cache-line-granularity--false-sharing)
   - [Snooping Protocols: MSI, MESI, MOESI](#23-snooping-protocols-msi-mesi-moesi)
   - [Non-Uniform Memory Access (NUMA)](#24-non-uniform-memory-access-numa)
3. [Software & Hardware Requirements](#3-software--hardware-requirements)
4. [Step-by-Step Commands & Screenshot Evidence](#4-step-by-step-commands--screenshot-evidence)
5. [Experimental Results & Data Analysis](#5-experimental-results--data-analysis)
   - [Part A: Protocol Simulation Metrics](#part-a-protocol-simulation-metrics)
   - [Part B: False Sharing Benchmark](#part-b-false-sharing-benchmark)
   - [Part C: NUMA Memory Sweep & Latency Benchmark](#part-c-numa-memory-sweep--latency-benchmark)
6. [Comparative Observation Table](#6-comparative-observation-table)
7. [Conclusion & Architectural Insights](#7-conclusion--architectural-insights)
8. [Directory Structure](#8-directory-structure)

---

## 1. Experiment Overview & Objective

In shared-memory multi-core processors, each core maintains dedicated private caches (L1/L2) alongside shared higher-level caches (L3). While private caches minimize memory latency, they introduce consistency hazards when multiple cores reference the same physical memory addresses.

### Core Objectives:
1. **Analyze Cache Coherence Protocols:** Simulate and quantify bus transactions, invalidations, memory write-backs, and cache-to-cache transfers across **MSI**, **MESI**, and **MOESI** protocols under shared and private access workloads.
2. **Evaluate False Sharing:** Measure the severe performance degradation caused when independent variables modified by concurrent threads occupy the same 64-byte cache line (adjacent layout) vs. when separated across distinct cache lines via 64-byte padding.
3. **Assess NUMA Memory Affinity:** Investigate the latency overhead of accessing local NUMA node memory versus remote memory across the interconnect using Linux NUMA policy utilities (`numactl`).

---

## 2. Theoretical Background

### 2.1 Why Cache Coherence is Needed
When multiple processor cores replicate the same memory location into their respective private L1/L2 caches, a write by one core renders copies in other caches stale. Without hardware coordination, subsequent reads by other cores would observe outdated data, violating program correctness. Cache coherence protocols enforce a uniform view of memory by coordinating cache reads and writes through snooping mechanisms over a shared bus or point-to-point interconnect.

### 2.2 Cache Line Granularity & False Sharing
Hardware cache coherence operates at the granularity of a **cache line** (typically 64 bytes), rather than individual bytes or variables.
- **False Sharing:** Occurs when two or more threads running on separate cores read and write distinct variables that reside within the exact same 64-byte cache line. 
- **The Penalty:** Even though the threads never access the same variable, each write invalidates the peer core's entire cache line, triggering a continuous ping-pong of cache line invalidations and bus reload transactions.
- **The Solution:** Padding or aligning data structures to 64-byte boundaries ensures each thread's active data is isolated to its own cache line.

```
Adjacent Layout (Shares 1 Cache Line - False Sharing):
+---------------+---------------+---------------------------------------+
| Core 0 Var x  | Core 1 Var y  | Unused / other data (64-byte line)    |
+---------------+---------------+---------------------------------------+

Padded Layout (Separated into distinct 64-byte Cache Lines):
Line A: +---------------+-----------------------------------------------+
        | Core 0 Var x  | 56 bytes padding                              |
        +---------------+-----------------------------------------------+
Line B: +---------------+-----------------------------------------------+
        | Core 1 Var y  | 56 bytes padding                              |
        +---------------+-----------------------------------------------+
```

### 2.3 Snooping Protocols: MSI, MESI, MOESI

| State | Name | Meaning | Memory Status | Other Caches Hold Copy? |
| :---: | :--- | :--- | :--- | :--- |
| **M** | Modified | Line is valid only in this cache and dirty (modified). | Stale (out-of-date) | No |
| **O** | Owned *(MOESI only)* | Dirty copy; this cache is owner and serves read requests. | Stale | Yes (as Shared) |
| **E** | Exclusive *(MESI/MOESI)* | Line is clean and present only in this cache. | Up-to-date | No |
| **S** | Shared | Line is clean (or dirty if owned in MOESI) and present in multiple caches. | Up-to-date (or owner holds) | Yes |
| **I** | Invalid | Cache line does not contain valid data. | N/A | N/A |

- **MSI Protocol:** The baseline 3-state protocol. Any write to a shared line requires an upgrade transaction (`BusUpgr`), and a write to private data loaded cleanly still triggers a bus transaction because MSI cannot differentiate between shared and unique clean lines.
- **MESI Protocol:** Introduces the **Exclusive (E)** state. A cache line fetched uniquely enters state `E`. Subsequent writes transition silently from `E -> M` without consuming bus bandwidth, dramatically accelerating private variable modifications.
- **MOESI Protocol:** Introduces the **Owned (O)** state. When a dirty (`M`) cache line is read by another core, the owner moves to `O` and serves the data directly via Cache-to-Cache transfer (`C2C`), eliminating the compulsory write-back to system memory.

### 2.4 Non-Uniform Memory Access (NUMA)
In modern multi-socket or multi-chiplet systems, physical memory is partitioned across multiple **NUMA nodes**. Cores achieve lowest latency and highest bandwidth when accessing RAM connected directly to their local memory controller (**Local Access**). Accessing memory connected to another socket requires traversing the inter-socket interconnect (**Remote Access**), resulting in higher latency.

---

## 3. Software & Hardware Requirements

| Component | Specification / Tool | Purpose |
| :--- | :--- | :--- |
| **Operating System** | Ubuntu 24.04.4 LTS (Linux 6.8.0-xx) | Host/Guest operating environment |
| **Virtualization** | VMware Workstation Pro | Virtual machine host with multi-node virtual NUMA topology |
| **Compiler** | GCC 13.3.0 (`build-essential`) | Compiling OpenMP parallel C benchmarks |
| **Parallel Library** | OpenMP (`libgomp`) | Thread management, synchronization, and high-precision timing |
| **NUMA Tools** | `numactl`, `hwloc` (`lscpu -e`) | Inspecting NUMA topology and binding thread execution/memory allocation |
| **Simulation** | Python 3.12.3 | Multi-core cache snooping protocol simulator |

---

## 4. Step-by-Step Commands & Screenshot Evidence

The following section details every execution step with its command, one-line explanation, and empirical terminal screenshot.

### Step 1: Update System Package Repositories
Update the local package index to guarantee availability of required toolchains.
```bash
sudo apt update
```
![Step 1: apt update](screenshots/01_apt_update.jpg)

---

### Step 2: Install Compiler Toolchain, NUMA Utilities, and Python
Install `build-essential` (GCC, G++, Make, OpenMP), `numactl`, `hwloc`, and `python3`.
```bash
sudo apt install build-essential numactl hwloc python3 -y
```
![Step 2: Install Dependencies](screenshots/02_install_dependencies.jpg)

---

### Step 3: Inspect CPU Architecture and NUMA Node Topology
Verify compiler and python versions, and inspect virtual NUMA nodes, socket layouts, and cache topologies.
```bash
gcc --version && python3 --version
numactl --hardware
lscpu -e
```
*One-line Explanation:* Inspects CPU core-to-socket mapping and verifies that the dual-node NUMA topology (Node 0 and Node 1) is active.
![Step 3: Hardware and NUMA Topology](screenshots/03_hardware_and_numa_topology.jpg)

---

### Step 4: Execute Cache Coherence Protocol Simulator
Run the Python cache coherence simulator to trace state transitions across MSI, MESI, and MOESI protocols over 1000 iterations.
```bash
python3 coherence_sim.py 1000
```
*One-line Explanation:* Simulates cache line state evolutions under two cores and counts bus transactions, invalidations, write-backs, and cache-to-cache transfers.
![Step 4: Coherence Simulator Traces](screenshots/04_coherence_sim_trace.jpg)
![Step 5: Coherence Simulator Totals](screenshots/05_coherence_sim_totals.jpg)

---

### Step 5: Compile & Execute False Sharing and NUMA Sweep Benchmarks
Compile individual benchmark programs with OpenMP acceleration and level-2 optimization.
```bash
gcc -O2 false_sharing.c -fopenmp -o false_sharing
OMP_NUM_THREADS=2 ./false_sharing adjacent
OMP_NUM_THREADS=2 ./false_sharing padded

gcc -O2 numa_sweep.c -fopenmp -o numa_sweep
OMP_NUM_THREADS=2 numactl --cpunodebind=0 --membind=0 ./numa_sweep
OMP_NUM_THREADS=2 numactl --cpunodebind=0 --membind=1 ./numa_sweep
```
*One-line Explanation:* Compiles and measures false sharing overhead with 2 threads, followed by evaluating 512 MB memory sweep under local and remote memory binding.
![Step 6: False Sharing and NUMA Sweep](screenshots/06_false_sharing_and_numa_sweep.jpg)

---

### Step 6: Multi-Run Statistical Evaluation of NUMA Memory Sweep
Run multiple iterations across 1 and 2 threads to obtain reliable median timings for local vs. remote memory passes.
```bash
for i in 1 2 3; do OMP_NUM_THREADS=1 numactl --cpunodebind=0 --membind=0 ./numa_sweep 512; done
for i in 1 2 3; do OMP_NUM_THREADS=2 numactl --cpunodebind=0 --membind=0 ./numa_sweep 512; done
for i in 1 2 3; do OMP_NUM_THREADS=1 numactl --cpunodebind=0 --membind=1 ./numa_sweep 512; done
for i in 1 2 3; do OMP_NUM_THREADS=2 numactl --cpunodebind=0 --membind=1 ./numa_sweep 512; done
```
*One-line Explanation:* Performs 3 consecutive runs per configuration to confirm stability of memory sweep timings across NUMA nodes.
![Step 7: Multi-Run NUMA Sweeps](screenshots/07_numa_sweep_multi_runs.jpg)

---

### Step 7: Unified Scalability Benchmark (Default System Placement)
Compile and execute the unified benchmark program testing false sharing scaling across 1, 2, and 4 threads alongside memory sweeps.
```bash
gcc -O2 compare_numa.c -fopenmp -o compare_numa
./compare_numa
```
*One-line Explanation:* Measures counter execution times for adjacent vs padded layouts across 1, 2, and 4 threads and times a 512 MB memory sweep without binding constraints.
![Step 8: Unified Benchmark Default](screenshots/08_compare_numa_default.jpg)

---

### Step 8: Unified Benchmark with Local Memory Binding (Node 0)
Execute the unified benchmark binding both CPU execution and memory allocation strictly to NUMA Node 0.
```bash
OMP_NUM_THREADS=2 numactl --cpunodebind=0 --membind=0 ./compare_numa
```
*One-line Explanation:* Enforces thread execution on Node 0 CPUs (0, 1) and memory allocation on local Node 0 RAM.
![Step 9: Node 0 Local Binding](screenshots/09_compare_numa_node0_local.jpg)

---

### Step 9: Unified Benchmark with Remote Memory Binding (Node 1)
Execute the unified benchmark binding CPU execution to Node 0 while forcing memory allocation on Node 1 across the interconnect.
```bash
OMP_NUM_THREADS=2 numactl --cpunodebind=0 --membind=1 ./compare_numa
```
*One-line Explanation:* Forces CPU threads on Node 0 to access remote RAM located on Node 1 to evaluate interconnect overhead.
![Step 10: Node 1 Remote Binding](screenshots/10_compare_numa_node1_remote.jpg)

---

## 5. Experimental Results & Data Analysis

### Part A: Protocol Simulation Metrics

The simulation models two cores executing interleaved read-write increments over 1000 iterations (total 4000 memory operations):

#### Simulation Summary (1000 Iterations)
| Layout | Protocol | Bus Transactions | BusRd | BusRdX | BusUpgr | Invalidations | Write-backs | Cache-to-Cache (C2C) | Silent E $\to$ M |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Adjacent** | **MSI** | **4000** | 2000 | 0 | 2000 | 1999 | 1999 | 0 | 0 |
| **Adjacent** | **MESI** | **3999** | 2000 | 0 | 1999 | 1999 | 1999 | 0 | **1** |
| **Adjacent** | **MOESI**| **3999** | 2000 | 0 | 1999 | 1999 | **0** | **1999** | **1** |
| **Padded** | **MSI** | **4** | 2 | 0 | 2 | 0 | 0 | 0 | 0 |
| **Padded** | **MESI** | **2** | 2 | 0 | 0 | 0 | 0 | 0 | **2** |
| **Padded** | **MOESI**| **2** | 2 | 0 | 0 | 0 | 0 | 0 | **2** |

#### Protocol Performance Graph
![Coherence Protocols Traffic](graphs/coherence_protocols_traffic.png)

#### Analytical Findings:
1. **MSI Bus Upgrade Overhead:** In MSI, because lines are initially loaded as Shared (`S`), every first write triggers a `BusUpgr` transaction. Under adjacent sharing, 2000 upgrades and 1999 write-backs are generated.
2. **MESI Private Data Advantage:** In padded mode, MESI loads private lines directly as Exclusive (`E`), allowing silent transitions (`E -> M`) with zero bus upgrade overhead (only 2 bus transactions total vs. 4 in MSI).
3. **MOESI Elimination of RAM Write-Backs:** In adjacent sharing, MOESI completely eliminates memory write-backs (**0** vs. 1999 in MSI/MESI) by utilizing the Owned (`O`) state and serving dirty data through direct **Cache-to-Cache transfers (1999 C2C transfers)**.

---

### Part B: False Sharing Benchmark

Workload: **100,000,000** total atomic increments distributed evenly across threads.

#### Table 1: Counter Execution Times (compare_numa Default Execution)
| Layout | Threads | Increments / Thread | Final Count | Correctness | Execution Time (s) | Speedup / Overhead |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Adjacent** | 1 | 100,000,000 | 100,000,000 | Correct | 0.0233 s | Baseline (1T) |
| **Padded** | 1 | 100,000,000 | 100,000,000 | Correct | 0.0220 s | Baseline (1T) |
| **Adjacent** | 2 | 50,000,000 | 100,000,000 | Correct | 0.0142 s | 1.64x speedup |
| **Padded** | 2 | 50,000,000 | 100,000,000 | Correct | **0.0111 s** | **1.98x speedup (Near Ideal)** |
| **Adjacent** | 4 | 25,000,000 | 100,000,000 | Correct | 0.0065 s | Cache contention |
| **Padded** | 4 | 25,000,000 | 100,000,000 | Correct | **0.0058 s** | **3.79x speedup** |

#### False Sharing Scaling Graph
![False Sharing Execution Time](graphs/false_sharing_execution_time.png)

#### Analytical Findings:
- At 2 threads, the **padded layout finishes in 0.0111 s**, outperforming the **adjacent layout (0.0142 s)** by **~28%**.
- In the adjacent layout, every store instruction invalidates the sibling core's L1 cache line, causing pipeline stalls while waiting for bus ownership transfers.
- 64-byte padding completely isolates thread writes, allowing each core's L1 cache to maintain the line in Modified (`M`) state without cross-core invalidation traffic.

---

### Part C: NUMA Memory Sweep & Latency Benchmark

Workload: **512 MB** buffer sequential read sweep (4 passes, stride = 64 bytes).

#### Table 2: 512 MB Memory Sweep Comparison
| Policy / Binding | CPU Node | Memory Node | Threads | Execution Time (s) | Access Characterization |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Default** | OS scheduled | OS First-Touch | 1 | 0.1178 s | Unbound baseline |
| **Default** | OS scheduled | OS First-Touch | 2 | 0.1061 s | Unbound 2-thread baseline |
| **Local Memory** | Node 0 | Node 0 | 1 | 0.1138 s | Pure local socket access |
| **Local Memory** | Node 0 | Node 0 | 2 | **0.1036 s** | **Optimal throughput** |
| **Remote Memory** | Node 0 | Node 1 | 1 | 0.1137 s | Interconnect traversal |
| **Remote Memory** | Node 0 | Node 1 | 2 | 0.1101 s | Interconnect bound |

#### NUMA Memory Sweep Latency Graph
![NUMA Memory Latency](graphs/numa_memory_latency.png)

#### Analytical Findings:
- Under 2 threads, local memory allocation (`--membind=0`) completes in **0.1036 s**, while forced remote allocation (`--membind=1`) takes **0.1101 s** (~6.3% latency penalty).
- On virtualized NUMA nodes sharing physical memory channels, memory timings remain relatively close. On bare-metal multi-socket systems with distinct physical DDR channels, remote access penalties typically range from **30% to 80%**.

---

## 6. Comparative Observation Table

| Case / Scenario | Correctness Guaranteed? | Relative Performance | Scalability Characteristics | Architectural Reason |
| :--- | :---: | :--- | :--- | :--- |
| **MSI Protocol** | Yes | Lowest among protocols | High bus traffic on shared lines | Must issue `BusUpgr` on every write to shared lines and write back dirty lines. |
| **MESI Protocol** | Yes | High for private data | High for private; degrades on shared | `Exclusive` state allows silent `E -> M` write hit with zero bus traffic. |
| **MOESI Protocol** | Yes | Highest for shared read/write | Best bus traffic reduction | `Owned` state serves data directly cache-to-cache, avoiding RAM write-backs. |
| **Adjacent Layout** *(False Sharing)* | Yes | Degraded (28% slower at 2T) | Sub-linear scaling | Cores continuously invalidate each other's L1 cache lines (ping-pong effect). |
| **Padded Layout** *(64-byte Align)* | Yes | Optimal (near-ideal speedup) | Near-linear scaling | Each core retains private ownership of its cache line in `Modified` state. |
| **Local NUMA Memory** | Yes | Reference (Fastest) | Scales with memory channels | Memory requests served by local integrated memory controller (IMC). |
| **Remote NUMA Memory** | Yes | Slower (~6-10% penalty on VM) | Limited by interconnect bandwidth | Requests must traverse UPI / Infinity Fabric interconnect. |

---

## 7. Conclusion & Architectural Insights

1. **Cache Coherence Overhead is Determined by Access Patterns:** All three protocols guarantee sequential consistency, but their bus bandwidth footprints differ fundamentally. MESI minimizes cost for thread-private data, while MOESI significantly optimizes workloads with active producer-consumer sharing by eliminating redundant RAM write-backs.
2. **False Sharing is a Hidden Performance Killer:** In multi-threaded programs, logical data independence does not guarantee physical independence. Allocating shared counters adjacent to each other on a 64-byte boundary induces continuous cache line thrashing. Applying explicit 64-byte cache-line padding completely resolves this issue.
3. **NUMA-Aware Memory Placement is Essential for Memory-Bound Scale:** Placing computation threads on the same NUMA node as their physical memory allocations avoids interconnect bottlenecks, maximizing overall memory throughput.

---

## 8. Directory Structure

```plaintext
4.Analyze-Cache-Coherence-and-NUMA-Memory-Access-Performance/
├── .gitignore
├── README.md
├── generate_graphs.py
├── coherence_sim.py
├── false_sharing.c
├── numa_sweep.c
├── compare_numa.c
├── graphs/
│   ├── coherence_protocols_traffic.png
│   ├── false_sharing_execution_time.png
│   └── numa_memory_latency.png
├── screenshots/
│   ├── 01_apt_update.jpg
│   ├── 02_install_dependencies.jpg
│   ├── 03_hardware_and_numa_topology.jpg
│   ├── 04_coherence_sim_trace.jpg
│   ├── 05_coherence_sim_totals.jpg
│   ├── 06_false_sharing_and_numa_sweep.jpg
│   ├── 07_numa_sweep_multi_runs.jpg
│   ├── 08_compare_numa_default.jpg
│   ├── 09_compare_numa_node0_local.jpg
│   └── 10_compare_numa_node1_remote.jpg
└── src/
    ├── coherence_sim.py
    ├── false_sharing.c
    ├── numa_sweep.c
    └── compare_numa.c
```
