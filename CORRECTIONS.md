# Corrections — 2026-10-25

## The "GAIA" task file is not GAIA

The branches `two_datasets`, `arixvplus_v2`, `codex-completeness-cb` and `version2_start` contain
`benchmark_eval/data/gaia_subset.jsonl`. Its name and task ids (`gaia_001` … `gaia_025`) suggest
tasks from the GAIA benchmark (Mialon et al., 2023). **They are not.** The file holds 25 simple
arithmetic tasks, short word problems and direct calculations, for example:

> `gaia_001`: "A store sells apples for $2 each. If you buy 3 apples and get a 20% discount on the
> total, what is the final price?" (reference answer `4.8`)
>
> `gaia_024`: "Return ONLY a number. What is 11 * 11?" (reference answer `121`)

`gaia_subset.jsonl.bkp` holds three placeholder samples marked "Replace with real benchmark data."
The GAIA-named task files on these four branches contain no GAIA benchmark questions. `main` does
not contain them.

**Consequences:**
- Every result record whose `task_id` starts with `gaia_` comes from these 25 arithmetic tasks. On
  `two_datasets` this includes `results/overnight_gaia_subset_*` (from `run_overnight.sh`),
  `results/observer_*` (from `run_observer_ladder.sh`) and `results/givens_corruption_p07_*` (from
  `run_givens_repeats.sh`). **Do not read or cite them as GAIA results.** They show behaviour on
  simple arithmetic only.
- The GSM8K files (`gsm8k_subset.jsonl`, `gsm8k_full.jsonl`) hold GSM8K test problems; this
  correction does not affect them.
- `benchmark_eval/src/gaia_loader.py` is a generic JSONL loader; its name does not imply GAIA data.

This correction changes no dataset file names or script references. Its findings were checked
against the branch heads named above on 2026-10-25.

## Scope

This note covers the dataset label only. It is placed on `main` (which does not contain these files)
so that visitors see it, and on each affected branch.
