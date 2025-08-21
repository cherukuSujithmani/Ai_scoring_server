# run_all.ps1
# PowerShell script to start Zookeeper + Kafka + FastAPI together


$KAFKA_HOME = "C:\kafka"             # your Kafka folder


$FASTAPI_APP = "C:\p_projects\Ai_scoring_server\app\main.py"   # your FastAPI app path

# Start Zookeeper
Write-Host "Starting Zookeeper..."
Start-Process powershell -ArgumentList "-NoExit", "-Command cd $KAFKA_HOME ; .\bin\windows\zookeeper-server-start.bat .\config\zookeeper.properties"

# Wait a bit for Zookeeper to fully start
Start-Sleep -Seconds 10

# Start Kafka broker
Write-Host "Starting Kafka Broker..."
Start-Process powershell -ArgumentList "-NoExit", "-Command cd $KAFKA_HOME ; .\bin\windows\kafka-server-start.bat .\config\server.properties"

# Wait for Kafka to initialize
Start-Sleep -Seconds 10

# Start FastAPI service
Write-Host "Starting FastAPI Service..."
Start-Process powershell -ArgumentList "-NoExit", "-Command cd $(Split-Path $FASTAPI_APP) ; uvicorn main:app --reload --port 8000"

Write-Host "✅ All services started (Zookeeper, Kafka, FastAPI)."
