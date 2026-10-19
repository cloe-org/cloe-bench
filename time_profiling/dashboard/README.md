# Results dashboard

The interactive page shared with the community: <https://claude.ai/artifact/AFS2bEJHWXWLBB86zg6W3X>.

- `build_dashboard_data.py` builds `data/*.json` from the committed results in `../studies/`. These are the dashboard's datasets, uploaded to it as attached files.
- `index.html` is the dashboard's page. Every figure on it is computed from those datasets.

To update the dashboard after new runs: re-run `build_dashboard_data.py`, then ask Claude (or edit the dashboard directly) to replace the attached files and, if needed, the page.
