# Circuit Breaker Patterns for Multi-Agent LLM Systems

[![Reproducible Research](https://img.shields.io/badge/Reproducible-Research-brightgreen.svg)](https://github.com/hamley241/circuit-breaker-agents)
[![Monte Carlo Validated](https://img.shields.io/badge/Monte%20Carlo-Validated-blue.svg)](COMPREHENSIVE_RESULTS_2026-03-30.md)

## Overview

This repository contains the complete implementation and experimental validation of circuit breaker patterns for multi-agent Large Language Model (LLM) systems. Our research demonstrates **up to 85% reduction in cascading failure rates** through comprehensive Monte Carlo simulation with 100,000+ trials.

## Key Results

| Circuit Breaker Type | Average CFR Reduction | Best Performance |
|---------------------|----------------------|------------------|
| SIMPLE_CB | ~7% | Traditional pattern |
| AI_CB | ~48% | Confidence-based logic |
| **ADAPTIVE_CB** | **~75%** | **Dynamic thresholds** |

### Scaling Performance (ADAPTIVE_CB)
- **Chain Length 2**: 50.4% CFR reduction
- **Chain Length 3**: 70.2% CFR reduction  
- **Chain Length 4**: 80.0% CFR reduction
- **Chain Length 5**: 85.3% CFR reduction
- **Chain Length 6**: 88.8% CFR reduction

## Quick Start

### Running the Monte Carlo Simulation

```bash
# Clone the repository
git clone https://github.com/hamley241/circuit-breaker-agents.git
cd circuit-breaker-agents

# Run v2 Monte Carlo simulation (recommended)
python3 circuit_breaker_montecarlo_v2.py --chain-length 5 --runs 5000

# Run original validation
python3 circuit_breaker_montecarlo_fixed.py --chain-length 5 --runs 5000
```

### Reproducing Published Results

```bash
# V1 Results (Original Monte Carlo)
python3 circuit_breaker_montecarlo_fixed.py --chain-length 5 --runs 5000

# V2 Results (Enhanced with Adaptive Thresholds)  
python3 circuit_breaker_montecarlo_v2.py --chain-length 5 --runs 5000
```

## Repository Structure

```
circuit-breaker-agents/
├── README.md                                    # This file
├── COMPREHENSIVE_RESULTS_2026-03-30.md        # Complete experimental documentation
├── circuit_breaker_montecarlo_fixed.py        # V1: Original Monte Carlo implementation
├── circuit_breaker_montecarlo_v2.py           # V2: Enhanced with dynamic thresholds
├── results/                                    # Experimental result data (JSON files)
│   ├── montecarlo_*.json                      # V1 results by chain length
│   └── montecarlo_v2_*.json                   # V2 enhanced results
└── [additional experimental artifacts]
```

## Research Paper

**"Circuit Breakers for Multi-Agent LLM Systems: Preventing Cascading Failures through Monte Carlo Validation"**

- **Abstract**: Demonstrates 50-89% cascading failure reduction across agent chain lengths
- **Methodology**: Monte Carlo simulation with 100,000+ trials  
- **Results**: Statistical significance across all circuit breaker variants
- **Reproducibility**: Complete version control and parameter documentation

## Technical Specifications

### Experimental Design
- **Total Trials**: 100,000+ across all configurations
- **Chain Lengths**: 2, 3, 4, 5, 6 agents  
- **Runs per Configuration**: 5,000 trials
- **Failure Rate**: 15% per agent (realistic production scenario)
- **Random Seed**: 42 (fixed for reproducibility)

### Circuit Breaker Types

1. **NO_CB**: No protection (baseline measurement)
2. **SIMPLE_CB**: Traditional two-state circuit breaker  
3. **AI_CB**: Four-state reasoning-aware circuit breaker
4. **ADAPTIVE_CB**: Dynamic threshold adjustment with chain-length optimization

### Key Metrics
- **CFR (Cascading Failure Rate)**: Primary outcome measure
- **Recovery Time**: Time from circuit open to successful recovery
- **False Positive Rate**: Unnecessary circuit activations
- **Computational Overhead**: Additional latency per request

## Statistical Validation

- **Sample Sizes**: 5,000+ runs per configuration for statistical robustness
- **Significance Testing**: All reported differences p < 0.001
- **Effect Sizes**: Large effect sizes (Cohen's h > 0.5) for primary comparisons
- **Reproducibility**: Fixed random seeds ensure identical results across runs

## Installation Requirements

```bash
# Python dependencies
pip install numpy random json datetime pathlib dataclasses enum typing

# Or using requirements.txt (if available)
pip install -r requirements.txt
```

## Usage Examples

### Basic Circuit Breaker Test
```python
from circuit_breaker_montecarlo_v2 import run_experiment

# Run comprehensive test across chain lengths
for chain_length in [2, 3, 4, 5, 6]:
    results = run_experiment(chain_length, runs=5000)
    print(f"Chain {chain_length}: {results}")
```

### Custom Configuration
```python
# Custom parameters
results = run_experiment(
    chain_length=4,
    runs=1000,
    failure_rate=0.20,  # Higher failure rate
    seed_base=100       # Different random seed
)
```

## Research Applications

This codebase supports research in:
- **Multi-agent LLM reliability**
- **Distributed systems fault tolerance**
- **AI safety and robustness**
- **Production LLM system design**

## Contributing

This repository represents completed research with validated results. For extensions or adaptations:

1. Fork the repository
2. Create feature branches for modifications  
3. Maintain reproducibility through version control
4. Document any changes to experimental parameters

## Citation

If you use this code or results in your research, please cite:

```bibtex
@article{circuit_breakers_2026,
  title={Circuit Breakers for Multi-Agent LLM Systems: Preventing Cascading Failures through Monte Carlo Validation},
  author={[Author]},
  year={2026},
  note={Monte Carlo validation with 100,000+ trials},
  url={https://github.com/hamley241/circuit-breaker-agents}
}
```

## License

MIT License - See LICENSE file for details.

## Contact

For questions about the research methodology or experimental design, please open an issue in this repository.

---

**Research Status**: ✅ Complete and validated
**Reproducibility**: ✅ Full version control and parameter documentation  
**Statistical Rigor**: ✅ 100,000+ Monte Carlo trials with significance testing