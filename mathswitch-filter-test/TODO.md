# What I have done

I added slurper with a filter. It filters for `def`, `structure`, `class` and `inductive`. I implemented it like that, because it was the most straightforward for implementations. In Issue #14 this way of filtering is one of the pruposed, but without `def`. I chose to add `def`, because otherwise we miss usefull blocks like [this](https://leanprover-community.github.io/mathlib4_docs/Mathlib/NumberTheory/ADEInequality.html#ADEInequality.Admissible) and I think it would be all right to have a filter that takes in more concepts, even if it means that we have more false positives
  


I designed a test (written by claude) to compare filters. You can run filters by runing 
`py run_filters` and than `py report` that generats html report
if you want to specify what llm you want to use ou can do so with flag


## Still todo: 

Add filters
