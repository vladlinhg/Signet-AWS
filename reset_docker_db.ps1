# Reset Database in Docker Container
Write-Host "Resetting Database in Docker..." -ForegroundColor Cyan

# 1. Flush Data
Write-Host "1. Flush Data..."
docker-compose exec -T web python manage.py flush --no-input

# 2. Migrate (Ensure Schema Updates)
Write-Host "2. Migrate Schema..."
docker-compose exec -T web python manage.py migrate

# 3. Initialize Static Data
Write-Host "3. Initialize Static Data..."
docker-compose exec -T web python manage.py init_project

Write-Host "Done! Database is clean and ready." -ForegroundColor Green
