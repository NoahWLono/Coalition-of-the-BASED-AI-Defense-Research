# Implementation plan

Goal: deliver the bounded mission in mission.txt with executable verification and local artifacts.

Architecture: plain JSON scenarios and schedules, a discrete-event simulator, a time-indexed MILP, and an independent checker. Python, SciPy/HiGHS and Matplotlib provide optimization and figures. The checker and tiny reference use standard Python only.

The user has authorized implementation and routine decisions without another approval. This new directory isolates files from unrelated concurrent projects. The parent repository has no initial commit, so a Git worktree cannot be based on it; no branch or sibling files will be changed.

- [x] Write the four-request fixture and schema, then implement independent checking with corruption tests before building the optimizer.
- [x] Implement an event-queue simulator with FCFS and earliest-deadline policies. Test boundaries and identical online history under changed unseen demand.
- [x] Implement bounded MILP scheduling with battery inventory flow, charging, staff, vehicle availability, and regional rejection fairness. Report raw status and bounds.
- [x] Independently enumerate tiny schedules and compare minima. Check integer-slot endpoint semantics and battery reuse.
- [x] Run 20-request offline and online comparisons, controlled demand/charger/weather/weight sweeps, and preserve every schedule plus validation.
- [x] Produce model, assumption register, data dictionary, source record, figures, command/version logs and reproduction guide. Review evidence and resolve material findings.

Review focus: incomplete rejection records, battery reuse without recharge, starts at resource-release boundaries, leaked online arrivals, and misleading time-limit bounds. Tests must exercise each.
