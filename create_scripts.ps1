# create_scripts.ps1
# This script creates a "scripts/" folder and populates it with helper shell scripts.

$scriptDir = Join-Path -Path $PSScriptRoot -ChildPath "scripts"

# Create scripts directory if it doesn't exist
if (-Not (Test-Path $scriptDir)) {
    New-Item -Path $scriptDir -ItemType Directory | Out-Null
    Write-Host "Created directory: $scriptDir"
} else {
    Write-Host "Directory already exists: $scriptDir"
}

# Define scripts and their contents
$scripts = @{
    "unit_tests.sh" = @"
#!/bin/bash
# Run fast unit tests without Docker
uv run pytest -m "not docker"
"@

    "integration_tests.sh" = @"
#!/bin/bash
# Run full integration tests with Docker
docker compose -f docker-compose.test.yml build --no-cache
docker compose -f docker-compose.test.yml up -d
docker compose -f docker-compose.test.yml exec ingestion_service uv run pytest -m "docker"
"@

    "reset_docker.sh" = @"
#!/bin/bash
# Reset Docker containers and volumes
docker-compose down -v
docker compose -f docker-compose.test.yml stop
docker compose -f docker-compose.test.yml down -v --remove-orphans
rm -rf ./volumes/ingestion*
docker rmi agentic-rag-ingestion-ingestion_service:latest
"@

    "reset_prod.sh" = @"
#!/bin/bash
# Reset and bring up production Docker containers
docker-compose down -v
docker compose stop
docker compose down -v --remove-orphans
rm -rf ./volumes/ingestion*
docker rmi agentic-rag-ingestion-ingestion_service:latest
docker compose build --no-cache
docker compose up -d
docker-compose exec ingestion_service uv run alembic upgrade head
"@

    "run_migrations.sh" = @"
#!/bin/bash
# Run Alembic migrations
docker-compose exec ingestion_service uv run alembic upgrade head
"@

    "sql_check.sh" = @"
#!/bin/bash
# Optional: sanity-check SQL tables
docker-compose exec postgres psql -U ingestion_user -d ingestion_test -c '\dn'
docker-compose exec postgres psql -U ingestion_user -d ingestion_test -c '\d ingestion_service.vectors'
docker-compose exec postgres psql -U ingestion_user -d ingestion_test -c 'SELECT * FROM ingestion_service.vectors;'
"@
}

# Create each script file
foreach ($name in $scripts.Keys) {
    $filePath = Join-Path $scriptDir $name
    $scripts[$name] | Out-File -FilePath $filePath -Encoding UTF8 -Force
    # Make script executable (for Unix/Mac)
    if ($IsLinux -or $IsMacOS) {
        chmod +x $filePath
    }
    Write-Host "Created script: $filePath"
}

Write-Host "All scripts have been created successfully in $scriptDir."
