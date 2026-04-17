# Data Maintenance

## Current Data Flow

The app uses a two-step data flow:

1. Edit source-of-truth data in the external `SciEdu_Central_Data` repo.
2. Sync those files into this repo under `SciEdu_Matrix_App/data/majors/`.

The Streamlit app reads local copies from:

- `SciEdu_Matrix_App/data/majors/sci_edu/`
- `SciEdu_Matrix_App/data/majors/physics/`

It does not read the external SSoT directly at runtime.

## Typical Update Workflow

1. Edit the external SSoT files, for example:
   `majors/sci_edu/matrix_2023.csv`
   `majors/sci_edu/program_2023.yaml`
   `majors/physics/matrix_2019.csv`
2. Preview the sync:
   `python deploy_data.py --dry`
3. Run the actual sync:
   `python deploy_data.py`
4. Update business timestamps if needed:
   `SciEdu_Matrix_App/data/majors/sci_edu/metadata.yaml`
   `SciEdu_Matrix_App/data/majors/physics/metadata.yaml`
5. Refresh the app and verify the result.

## Sync Script

`deploy_data.py` supports:

- auto-detecting this repo root
- auto-detecting sibling `../SciEdu_Central_Data`
- overriding the SSoT path with `SCIEDU_SSOT_DIR`

Examples:

```bash
python deploy_data.py --dry
python deploy_data.py --major sci_edu
SCIEDU_SSOT_DIR=/path/to/SciEdu_Central_Data python deploy_data.py
```

## Sidebar Update Time

Sidebar update info now prefers `metadata.yaml`:

```yaml
versions:
  "2023版":
    updated_at: "2026-04-17 14:30"
    note: "已同步最新培养方案矩阵"
```

If `updated_at` is missing, the app falls back to the data file's last modified time.
