<#
api credentials needed for auth
permissions needed for this script
device - READ
device.deregistered - DELETE
#>
$apiSecretKey = "xxx"
$apiId = "xxx"
#number of devices to execute against
$rows = 100
#log file location
$logFileLocation = "c:\temp\"
#simulate or execute, $simulate = true will save list of devices to be deleted to log file but not delete, false will create log file and delete
$simulate = $true
#timestamp of execution to be used for log file name
$timestamp = Get-Date -Format "MMddyyyyHHmmss"
#urls to be used for calls to api
$deviceSearchUrl = "https://defense.conferdeploy.net/appservices/v6/orgs/xxx/devices/_search"
$deviceActionUrl = "https://defense.conferdeploy.net/appservices/v6/orgs/xxx/device_actions"

#headers used for auth and return types
$headers = @{
    "X-Auth-Token" = $apiSecretKey + "/" + $apiId #X-Auth-Token: [API Secret Key]/[API ID]"
    "Content-Type" = "application/json"
    "Accept" = "application/json;odata=fullmetadata"
    }

#post body to return DEREGISTERED devices
$searchPayload = [PSCustomObject]@{
    criteria = [PSCustomObject]@{
        status = @("DEREGISTERED")
        os = @("linux") 
        }
    rows = $rows
    start = 0
}

#convert search payload to json
$searchPayloadJSON = ConvertTo-Json -InputObject $searchPayload -Compress
#post to query for deregistered linux devices and store results in variable
$searchResponse = Invoke-RestMethod -Method Post -Uri $deviceSearchUrl -Headers $headers -Body $searchPayloadJSON -Verbose
#create log file and array of device ids to be deleted
Add-Content -Path $logFileLocation"deleteDeregistered"$timestamp".log" -Value ("simulate = " + [string]$simulate)
Add-Content -Path $logFileLocation"deleteDeregistered"$timestamp".log" -Value "device_id device_name device_status"
if($searchResponse.results.Count -gt 0){
    [System.Collections.ArrayList]$deviceIds = @()
    foreach($device in $searchResponse.results){
        Add-Content -Path $logFileLocation"deleteDeregistered"$timestamp".log" -Value ([string]$device.id+" "+$device.name+" "+ $device.status)
        [void]$deviceIds.Add($device.id)
    }
    
    if($simulate -eq $false){
        #post body to call device action to delete DEREGISTERED devices
        $actionPayload = [PSCustomObject]@{
            action_type = "DELETE_SENSOR"
            device_id = $deviceIds
        }
        #convert action apyload to json
        $actionPayloadJSON = ConvertTo-Json -InputObject $actionPayload -Compress
        #post to delete deregistered linux devices and store results in variable
        $actionResponse = Invoke-RestMethod -Method Post -Uri $deviceActionUrl -Headers $headers -Body $actionPayloadJSON -Verbose
    }
}
Write-Output "Simulate = " [string]$simulate " " $searchResponse.results.Count.ToString() " devices have been deleted. Log file generated at " $logFileLocation"deleteDeregistered"$timestamp".log"