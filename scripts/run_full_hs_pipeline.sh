#!/bin/bash
#
# HS Player-Season Data Pipeline - Full Workflow Runner
#
# Runs the complete pipeline: validation → backfill → load → QA
# for all green datasources.
#
# Usage:
#   ./scripts/run_full_hs_pipeline.sh                    # All green sources
#   ./scripts/run_full_hs_pipeline.sh --source eybl      # EYBL only
#   ./scripts/run_full_hs_pipeline.sh --dry-run          # Test without backfill
#
# Author: Phase 16.1 - First Data Production Run
# Date: 2025-11-16

set -e  # Exit on error

# ==============================================================================
# Configuration
# ==============================================================================

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Directories
DATA_DIR="data"
SCRIPTS_DIR="scripts"
CONFIG_DIR="config"
REPORTS_DIR="reports"

# Database
DB_PATH="${DATA_DIR}/hs_player_seasons.duckdb"

# Default settings
SOURCE_FILTER=""
DRY_RUN=false
SKIP_VALIDATION=false
SKIP_QA=false

# ==============================================================================
# Parse Arguments
# ==============================================================================

while [[ $# -gt 0 ]]; do
    case $1 in
        --source)
            SOURCE_FILTER="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --skip-validation)
            SKIP_VALIDATION=true
            shift
            ;;
        --skip-qa)
            SKIP_QA=true
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --source NAME         Run pipeline for specific source only (e.g., eybl, sblive)"
            echo "  --dry-run             Run validation but skip backfill"
            echo "  --skip-validation     Skip validation step (not recommended)"
            echo "  --skip-qa             Skip QA step"
            echo "  --help                Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                           # Run full pipeline for all green sources"
            echo "  $0 --source eybl             # Run EYBL only"
            echo "  $0 --source sblive --dry-run # Test SBLive validation without backfill"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Run '$0 --help' for usage information"
            exit 1
            ;;
    esac
done

# ==============================================================================
# Helper Functions
# ==============================================================================

log_step() {
    echo -e "${BLUE}===================================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}===================================================================${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

check_dependencies() {
    log_step "Checking Dependencies"

    if ! command -v python &> /dev/null; then
        log_error "Python not found. Please install Python 3.8+"
        exit 1
    fi

    log_success "Python found: $(python --version)"

    # Check for required Python packages
    python -c "import pandas; import pyarrow; import duckdb" 2>/dev/null
    if [ $? -ne 0 ]; then
        log_warning "Some Python dependencies missing. Installing..."
        pip install pandas pyarrow duckdb
    fi

    log_success "All dependencies OK"
}

create_directories() {
    log_step "Creating Directories"

    mkdir -p "${DATA_DIR}/eybl"
    mkdir -p "${DATA_DIR}/sblive"
    mkdir -p "${REPORTS_DIR}"

    log_success "Directories created"
}

# ==============================================================================
# Pipeline Steps
# ==============================================================================

run_validation() {
    local source=$1

    log_step "Step 1: Semantic Validation - ${source}"

    if [ "$SKIP_VALIDATION" = true ]; then
        log_warning "Skipping validation (--skip-validation)"
        return 0
    fi

    local cmd="python ${SCRIPTS_DIR}/validate_datasource_stats.py --source ${source} --verbose"

    echo "Running: $cmd"
    if $cmd; then
        log_success "Validation passed for ${source}"
        return 0
    else
        log_error "Validation failed for ${source}"
        log_error "Fix validation errors before proceeding with backfill"
        return 1
    fi
}

run_eybl_backfill() {
    log_step "Step 2: EYBL Backfill → Parquet"

    if [ "$DRY_RUN" = true ]; then
        log_warning "Dry run mode - skipping backfill"
        return 0
    fi

    local cmd="python ${SCRIPTS_DIR}/backfill_eybl_player_seasons.py --seasons 2024 2023 2022"

    echo "Running: $cmd"
    if $cmd; then
        log_success "EYBL backfill complete"

        # Check parquet files
        local file_count=$(find ${DATA_DIR}/eybl -name "*.parquet" 2>/dev/null | wc -l)
        log_success "Generated ${file_count} EYBL parquet file(s)"
        return 0
    else
        log_error "EYBL backfill failed"
        return 1
    fi
}

run_sblive_backfill() {
    log_step "Step 2: SBLive Backfill → Parquet"

    if [ "$DRY_RUN" = true ]; then
        log_warning "Dry run mode - skipping backfill"
        return 0
    fi

    # Default to WA, OR, CA for first run
    # TODO: Read from config which states are green
    local states="WA OR CA"
    local season="2024-25"

    local cmd="python ${SCRIPTS_DIR}/backfill_sblive_player_seasons.py --states ${states} --season ${season}"

    echo "Running: $cmd"
    if $cmd; then
        log_success "SBLive backfill complete"

        # Check parquet files
        local file_count=$(find ${DATA_DIR}/sblive -name "*.parquet" 2>/dev/null | wc -l)
        log_success "Generated ${file_count} SBLive parquet file(s)"
        return 0
    else
        log_error "SBLive backfill failed"
        return 1
    fi
}

load_to_duckdb() {
    log_step "Step 3: Load to DuckDB"

    if [ "$DRY_RUN" = true ]; then
        log_warning "Dry run mode - skipping DuckDB load"
        return 0
    fi

    local cmd="python ${SCRIPTS_DIR}/load_to_duckdb.py"

    if [ -n "$SOURCE_FILTER" ]; then
        cmd="$cmd --sources ${SOURCE_FILTER}"
    fi

    echo "Running: $cmd"
    if $cmd; then
        log_success "DuckDB load complete"
        log_success "Database: ${DB_PATH}"
        return 0
    else
        log_error "DuckDB load failed"
        return 1
    fi
}

run_qa() {
    log_step "Step 4: Quality Assurance"

    if [ "$SKIP_QA" = true ]; then
        log_warning "Skipping QA (--skip-qa)"
        return 0
    fi

    if [ "$DRY_RUN" = true ]; then
        log_warning "Dry run mode - skipping QA"
        return 0
    fi

    local report_file="${REPORTS_DIR}/qa_full_$(date +%Y%m%d_%H%M%S).md"

    local cmd="python ${SCRIPTS_DIR}/qa_player_seasons.py --export-report ${report_file}"

    if [ -n "$SOURCE_FILTER" ]; then
        cmd="$cmd --source ${SOURCE_FILTER}"
        report_file="${REPORTS_DIR}/qa_${SOURCE_FILTER}_$(date +%Y%m%d_%H%M%S).md"
    fi

    echo "Running: $cmd"
    if $cmd; then
        log_success "QA checks passed"
        log_success "QA report: ${report_file}"
        return 0
    else
        log_warning "QA checks failed - review report for details"
        log_warning "QA report: ${report_file}"
        return 1
    fi
}

# ==============================================================================
# Main Pipeline
# ==============================================================================

main() {
    echo ""
    log_step "HS Player-Season Data Pipeline"
    echo ""
    echo "Source filter: ${SOURCE_FILTER:-all green sources}"
    echo "Dry run: ${DRY_RUN}"
    echo ""

    # Check dependencies
    check_dependencies

    # Create directories
    create_directories

    # Run pipeline based on source filter
    if [ -z "$SOURCE_FILTER" ] || [ "$SOURCE_FILTER" = "eybl" ]; then
        echo ""
        log_step "Processing EYBL"

        if run_validation "eybl"; then
            run_eybl_backfill
        else
            log_error "Skipping EYBL backfill due to validation failures"
        fi
    fi

    if [ -z "$SOURCE_FILTER" ] || [ "$SOURCE_FILTER" = "sblive" ]; then
        echo ""
        log_step "Processing SBLive"

        if run_validation "sblive"; then
            run_sblive_backfill
        else
            log_error "Skipping SBLive backfill due to validation failures"
        fi
    fi

    # Load to DuckDB (combines all sources)
    if [ "$DRY_RUN" = false ]; then
        echo ""
        load_to_duckdb

        # Run QA
        echo ""
        run_qa
    fi

    # Final summary
    echo ""
    log_step "Pipeline Summary"

    if [ "$DRY_RUN" = true ]; then
        log_warning "DRY RUN - No data was produced"
        log_warning "Run without --dry-run to actually generate parquet files"
    else
        log_success "Pipeline complete!"

        # Count parquet files
        local eybl_count=$(find ${DATA_DIR}/eybl -name "*.parquet" 2>/dev/null | wc -l)
        local sblive_count=$(find ${DATA_DIR}/sblive -name "*.parquet" 2>/dev/null | wc -l)

        echo ""
        echo "Parquet files generated:"
        echo "  - EYBL: ${eybl_count} file(s)"
        echo "  - SBLive: ${sblive_count} file(s)"
        echo ""
        echo "DuckDB database: ${DB_PATH}"
        echo ""

        if [ -f "${DB_PATH}" ]; then
            log_success "Query your data with:"
            echo ""
            echo "  duckdb ${DB_PATH} \"SELECT source, season, COUNT(*) FROM hs_player_seasons GROUP BY source, season;\""
            echo ""
        fi
    fi

    echo ""
}

# Run main pipeline
main

exit 0
