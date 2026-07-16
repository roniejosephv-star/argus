# Zenoh Recommendation: OPTIONAL
**Your system has sufficient RAM for full DDS.** Zenoh beneficial for:
- Multi-robot / fleet scenarios
- Cloud-edge bridging
- Low-latency requirements (<100μs)
- Mesh networking

## When to Consider Zenoh
- Deploying across unreliable networks (WiFi, 5G)
- Mixing micro-ROS and full ROS 2 nodes
- Need for efficient topic routing at scale

## Basic Config
```yaml
mode: peer
connect:
  - tcp/localhost:7447
```