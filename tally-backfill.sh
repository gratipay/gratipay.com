#!/bin/sh
patterns=("Linking" 
          "Already linked"
          "UnknownExchange" 
          "UnknownRoute"
          )
N=0
for pattern in "${patterns[@]}"; do
    n=`grep "$pattern" backfill.log | wc -l`
    N=`expr $n + $N`
    printf "%-28s %5s\n" "\"$pattern\"" $n
done
echo "----------------------------------"
printf "%-28s %5s\n" "" $N

echo

morepats=(
    "exchange_id in transaction"
    "triangulated an exchange"
    "exchange has a route"
    "card matches a route"
    "created a route"
)

for pattern in "${morepats[@]}"; do
    n=`grep "$pattern" backfill.log | wc -l`
    printf "%-28s %5s\n" "\"$pattern\"" $n
done
