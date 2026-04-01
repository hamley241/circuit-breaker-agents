for pf in 0.5 0.6 0.7 0.8
do
  python simulate_circuit_breakers.py --runs 10000 --p-f $pf --csv-out results_pf_$pf.csv
done
