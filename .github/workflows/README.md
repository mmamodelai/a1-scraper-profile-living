# UFC Fighter Stats - GitHub Actions

This directory contains 4 manual GitHub Actions workflows for the UFC Fighter Stats pipeline.

## Workflow Overview

### 1. **01-scrape-ufc.yml** - Scrape UFC Data
- **Purpose**: Scrapes UFC.com fighter profiles
- **Input**: `fighters_name.csv` (603 active fighters)
- **Output**: UFC HTML files in `fighter_profiles/` directory
- **Trigger**: Manual only (`workflow_dispatch`)

### 2. **02-scrape-espn.yml** - Scrape ESPN Data  
- **Purpose**: Scrapes ESPN.com fighter stats for per-fight data
- **Input**: `fighters_name.csv` (603 active fighters)
- **Output**: ESPN HTML files + per-fight CSV files
- **Trigger**: Manual only (`workflow_dispatch`)

### 3. **03-build-fighter-profiles.yml** - Build Fighter Profiles
- **Purpose**: Processes UFC HTML files into career data
- **Input**: UFC HTML files from step 1
- **Output**: `fighter_profiles.csv` (career totals)
- **Trigger**: Manual only (`workflow_dispatch`)

### 4. **04-build-position-stats.yml** - Build Position Stats
- **Purpose**: Processes ESPN data into per-fight statistics
- **Input**: ESPN CSV files from step 2
- **Output**: `striking_data.csv`, `clinch_data.csv`, `ground_data.csv`
- **Trigger**: Manual only (`workflow_dispatch`)

## How to Use

### Manual Trigger Steps:

1. **Go to GitHub Repository** → **Actions** tab
2. **Select the workflow** you want to run (01, 02, 03, or 04)
3. **Click "Run workflow"** button
4. **Configure inputs** if needed (defaults are usually correct)
5. **Click "Run workflow"** to start

### Typical Workflow Order:

```
fighters_name.csv
    ↓
01-scrape-ufc.yml → UFC HTML files
    ↓
02-scrape-espn.yml → ESPN HTML files + per-fight CSVs  
    ↓
03-build-fighter-profiles.yml → fighter_profiles.csv
    ↓
04-build-position-stats.yml → position stats CSVs
```

## Artifacts

Each workflow uploads artifacts that you can download:
- **HTML files**: Raw scraped data (30-day retention)
- **CSV files**: Processed data (30-day retention)
- **Logs**: Processing summaries and error reports

## Notes

- **Manual triggers only**: No automatic scheduling to avoid rate limiting
- **Ubuntu runners**: All workflows run on `ubuntu-latest`
- **Python 3.11**: Consistent Python version across all workflows
- **30-day retention**: Artifacts are automatically cleaned up after 30 days
- **Dependencies**: Each workflow installs only the packages it needs

## Future Enhancements

Once these workflows are working perfectly, we can add:
- **Scheduled triggers** (weekly/monthly updates)
- **Dependency between workflows** (auto-trigger next step)
- **Data validation** and quality checks
- **Email notifications** for completion/failures 