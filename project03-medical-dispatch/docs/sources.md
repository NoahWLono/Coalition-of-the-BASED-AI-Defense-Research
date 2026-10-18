# Source and execution record

Access date: 2026-10-17, America/Toronto. All fixtures, annotations, code and interpretations were produced by AI assistants in this session. There was no human subject data or qualified operational review.

- [Google OR-Tools scheduling](https://developers.google.com/optimization/scheduling): inspected as a scheduling-model starting point. OR-Tools is not a runtime dependency.
- [Google CP-SAT solver](https://developers.google.com/optimization/cp/cp_solver): inspected its distinctions between feasible, optimal, infeasible and unknown results. No CP-SAT results are claimed.
- [SciPy milp documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.milp.html): inspected time limits, integer variables, status codes, dual bounds and relative gaps. The online documentation identified itself as SciPy 1.18.0; execution uses pinned SciPy 1.17.1. The version-specific 1.17.1 web URL was inaccessible through the browsing tool. The installed API and docstring were checked before execution.

No outside data, weather service, medical standards or geographic source is used. The model concerns illustrative scheduling parameters only. No spending, publication or external account operations are part of this work.

The available workspace filesystem and local shell were explicitly supplied in the session environment. Python 3.14.8 and bundled Python 3.12.14 were inspected; neither initially contained SciPy or Matplotlib. A project-local virtual environment uses Python 3.12.14. Pinned packages were downloaded from the configured package index, without paid resources. requirements-lock.txt records the resolved dependencies.
