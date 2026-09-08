param(
    [Parameter(Mandatory = $true)]
    [string[]]$InputPaths,

    [Parameter(Mandatory = $true)]
    [string]$OutputDir,

    [double]$NominalCapacityAh = 1175.0,
    [double]$RateBasisPowerW = 3139.6
)

$ErrorActionPreference = "Stop"

function Get-ColumnMap {
    param([object[,]]$Values, [int]$ColumnCount)
    $map = @{}
    for ($c = 1; $c -le $ColumnCount; $c++) {
        $name = [string]$Values[1, $c]
        if ($name) {
            $map[$name] = $c
        }
    }
    return $map
}

function Get-Number {
    param($Value)
    if ($null -eq $Value -or $Value -eq "") {
        return 0.0
    }
    return [double]$Value
}

function Get-IsoTimestamp {
    param($Value)
    if ($Value -is [double] -or $Value -is [int]) {
        return [DateTime]::FromOADate([double]$Value).ToString("yyyy-MM-dd HH:mm:ss.fff")
    }
    return [string]$Value
}

function Get-RateLabel {
    param([double]$TargetPowerW, [double]$BasisPowerW)
    $rate = $TargetPowerW / $BasisPowerW
    return ("{0:0.0}P" -f $rate)
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$chargeRows = [System.Collections.Generic.List[object]]::new()
$dischargeRows = [System.Collections.Generic.List[object]]::new()
$summaryRows = [System.Collections.Generic.List[object]]::new()
$sourceRecords = [System.Collections.Generic.List[object]]::new()

$excel = New-Object -ComObject Excel.Application
$excel.Visible = $false
$excel.DisplayAlerts = $false

try {
    foreach ($inputPath in $InputPaths) {
        $book = $excel.Workbooks.Open($inputPath, 0, $true)
        try {
            $infoSheet = $book.Worksheets.Item("测试信息")
            $device = [string]$infoSheet.Cells.Item(8, 1).Text
            $channel = [string]$infoSheet.Cells.Item(8, 3).Text
            $cellId = [string]$infoSheet.Cells.Item(8, 5).Text

            $protocolSheet = $book.Worksheets.Item("项目内容")
            $protocolValues = $protocolSheet.UsedRange.Value2
            $protocolPower = @{}
            for ($r = 2; $r -le $protocolSheet.UsedRange.Rows.Count; $r++) {
                $sequence = [int](Get-Number $protocolValues[$r, 1])
                $setting = [string]$protocolValues[$r, 4]
                if ($setting -match "功率=([0-9.]+)\s*W") {
                    $protocolPower[$sequence] = [double]$Matches[1]
                }
            }

            $stepSheet = $book.Worksheets.Item("工步层")
            $stepRange = $stepSheet.UsedRange
            $stepValues = $stepRange.Value2
            $stepMap = Get-ColumnMap -Values $stepValues -ColumnCount $stepRange.Columns.Count
            $stepMeta = @{}

            for ($r = 2; $r -le $stepRange.Rows.Count; $r++) {
                $state = [string]$stepValues[$r, $stepMap["工步状态"]]
                if ($state -notmatch "^(充电|放电)") {
                    continue
                }

                $direction = if ($state.StartsWith("充电")) { "charge" } else { "discharge" }
                $cycleIndex = [int](Get-Number $stepValues[$r, $stepMap["循环序号"]])
                $stepIndex = [int](Get-Number $stepValues[$r, $stepMap["步次"]])
                $originalStep = [int](Get-Number $stepValues[$r, $stepMap["原始步次"]])
                $targetPowerW = if ($protocolPower.ContainsKey($originalStep)) {
                    [double]$protocolPower[$originalStep]
                } else {
                    0.0
                }

                $capacityAh = if ($direction -eq "charge") {
                    [Math]::Abs((Get-Number $stepValues[$r, $stepMap["充电容量(Ah)"]]))
                } else {
                    [Math]::Abs((Get-Number $stepValues[$r, $stepMap["放电容量(Ah)"]]))
                }
                $energyWh = if ($direction -eq "charge") {
                    [Math]::Abs((Get-Number $stepValues[$r, $stepMap["充电能量(Wh)"]]))
                } else {
                    [Math]::Abs((Get-Number $stepValues[$r, $stepMap["放电能量(Wh)"]]))
                }

                $segmentRole = if ($capacityAh -lt 0.05 * $NominalCapacityAh) { "supplementary" } else { "main" }
                $segmentKey = "$cycleIndex|$stepIndex"
                $stepMeta[$segmentKey] = [ordered]@{
                    cell_id = $cellId
                    device = $device
                    channel = $channel
                    direction = $direction
                    cycle_index = $cycleIndex
                    step_index = $stepIndex
                    original_step = $originalStep
                    state = $state
                    segment_role = $segmentRole
                    rate_label = Get-RateLabel -TargetPowerW $targetPowerW -BasisPowerW $RateBasisPowerW
                    rate_value = $targetPowerW / $RateBasisPowerW
                    target_power_W = $targetPowerW
                    start_time = Get-IsoTimestamp $stepValues[$r, $stepMap["开始时间"]]
                    end_time = Get-IsoTimestamp $stepValues[$r, $stepMap["结束时间"]]
                    start_voltage_V = Get-Number $stepValues[$r, $stepMap["起始电压(V)"]]
                    end_voltage_V = Get-Number $stepValues[$r, $stepMap["结束电压(V)"]]
                    start_current_A = Get-Number $stepValues[$r, $stepMap["起始电流(A)"]]
                    end_current_A = Get-Number $stepValues[$r, $stepMap["结束电流(A)"]]
                    capacity_Ah = $capacityAh
                    energy_Wh = $energyWh
                    duration = [string]$stepValues[$r, $stepMap["持续时间(h:min:s.ms)"]]
                    source_file = [IO.Path]::GetFileName($inputPath)
                }
            }

            $recordSheet = $book.Worksheets.Item("记录层")
            $recordRange = $recordSheet.UsedRange
            $recordValues = $recordRange.Value2
            $recordMap = Get-ColumnMap -Values $recordValues -ColumnCount $recordRange.Columns.Count
            $segmentStartMs = @{}
            $segmentStartCapacity = @{}
            $segmentStartEnergy = @{}
            $segmentPointIndex = @{}
            $curveEnd = @{}

            for ($r = 2; $r -le $recordRange.Rows.Count; $r++) {
                $state = [string]$recordValues[$r, $recordMap["工步状态"]]
                if ($state -notmatch "^(充电|放电)") {
                    continue
                }

                $cycleIndex = [int](Get-Number $recordValues[$r, $recordMap["循环序号"]])
                $stepIndex = [int](Get-Number $recordValues[$r, $recordMap["步次"]])
                $segmentKey = "$cycleIndex|$stepIndex"
                if (-not $stepMeta.ContainsKey($segmentKey)) {
                    continue
                }
                $meta = $stepMeta[$segmentKey]

                $continuousMs = Get-Number $recordValues[$r, $recordMap["连续时间"]]
                $rawCapacity = Get-Number $recordValues[$r, $recordMap["容量(Ah)"]]
                $rawEnergy = Get-Number $recordValues[$r, $recordMap["能量(Wh)"]]
                if (-not $segmentStartMs.ContainsKey($segmentKey)) {
                    $segmentStartMs[$segmentKey] = $continuousMs
                    $segmentStartCapacity[$segmentKey] = $rawCapacity
                    $segmentStartEnergy[$segmentKey] = $rawEnergy
                    $segmentPointIndex[$segmentKey] = 0
                }

                $segmentPointIndex[$segmentKey] = [int]$segmentPointIndex[$segmentKey] + 1
                $capacityAh = [Math]::Abs($rawCapacity - [double]$segmentStartCapacity[$segmentKey])
                $energyWh = [Math]::Abs($rawEnergy - [double]$segmentStartEnergy[$segmentKey])
                $rowObject = [pscustomobject][ordered]@{
                    cell_id = $cellId
                    device = $device
                    channel = $channel
                    direction = $meta.direction
                    cycle_index = $cycleIndex
                    step_index = $stepIndex
                    segment_role = $meta.segment_role
                    rate_label = $meta.rate_label
                    rate_value = [double]$meta.rate_value
                    target_power_W = [double]$meta.target_power_W
                    point_index = [int]$segmentPointIndex[$segmentKey]
                    elapsed_time_s = ($continuousMs - [double]$segmentStartMs[$segmentKey]) / 1000.0
                    timestamp = Get-IsoTimestamp $recordValues[$r, $recordMap["绝对时间"]]
                    voltage_V = Get-Number $recordValues[$r, $recordMap["实际电压(V)"]]
                    current_A = Get-Number $recordValues[$r, $recordMap["实际电流(A)"]]
                    capacity_Ah = $capacityAh
                    energy_Wh = $energyWh
                    raw_capacity_Ah = $rawCapacity
                    raw_energy_Wh = $rawEnergy
                    source_file = [IO.Path]::GetFileName($inputPath)
                }
                if ($meta.direction -eq "charge") {
                    $chargeRows.Add($rowObject)
                } else {
                    $dischargeRows.Add($rowObject)
                }
                $curveEnd[$segmentKey] = [ordered]@{
                    capacity_Ah = $capacityAh
                    energy_Wh = $energyWh
                    point_count = [int]$segmentPointIndex[$segmentKey]
                }
            }

            foreach ($segmentKey in $stepMeta.Keys) {
                $meta = $stepMeta[$segmentKey]
                $curve = $curveEnd[$segmentKey]
                $summaryRows.Add([pscustomobject][ordered]@{
                    cell_id = $meta.cell_id
                    device = $meta.device
                    channel = $meta.channel
                    direction = $meta.direction
                    cycle_index = $meta.cycle_index
                    step_index = $meta.step_index
                    original_step = $meta.original_step
                    segment_role = $meta.segment_role
                    rate_label = $meta.rate_label
                    rate_value = [double]$meta.rate_value
                    target_power_W = [double]$meta.target_power_W
                    capacity_Ah = [double]$meta.capacity_Ah
                    energy_Wh = [double]$meta.energy_Wh
                    mean_voltage_V = if ($meta.capacity_Ah -ne 0) { [double]$meta.energy_Wh / [double]$meta.capacity_Ah } else { 0.0 }
                    start_voltage_V = [double]$meta.start_voltage_V
                    end_voltage_V = [double]$meta.end_voltage_V
                    start_current_A = [double]$meta.start_current_A
                    end_current_A = [double]$meta.end_current_A
                    duration = $meta.duration
                    curve_point_count = if ($curve) { [int]$curve.point_count } else { 0 }
                    curve_end_capacity_Ah = if ($curve) { [double]$curve.capacity_Ah } else { 0.0 }
                    curve_end_energy_Wh = if ($curve) { [double]$curve.energy_Wh } else { 0.0 }
                    capacity_delta_Ah = if ($curve) { [double]$curve.capacity_Ah - [double]$meta.capacity_Ah } else { 0.0 }
                    energy_delta_Wh = if ($curve) { [double]$curve.energy_Wh - [double]$meta.energy_Wh } else { 0.0 }
                    start_time = $meta.start_time
                    end_time = $meta.end_time
                    source_file = $meta.source_file
                })
            }

            $sourceRecords.Add([pscustomobject][ordered]@{
                cell_id = $cellId
                device = $device
                channel = $channel
                source_path = $inputPath
                source_file = [IO.Path]::GetFileName($inputPath)
                record_rows = $recordRange.Rows.Count - 1
                extracted_charge_rows = ($chargeRows | Where-Object source_file -eq ([IO.Path]::GetFileName($inputPath))).Count
                extracted_discharge_rows = ($dischargeRows | Where-Object source_file -eq ([IO.Path]::GetFileName($inputPath))).Count
            })
        }
        finally {
            $book.Close($false)
        }
    }
}
finally {
    $excel.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($excel) | Out-Null
}

$chargePath = Join-Path $OutputDir "charge_curves_long.csv"
$dischargePath = Join-Path $OutputDir "discharge_curves_long.csv"
$summaryPath = Join-Path $OutputDir "rate_summary.csv"
$manifestPath = Join-Path $OutputDir "processing_manifest.json"

$chargeRows | Export-Csv -LiteralPath $chargePath -NoTypeInformation -Encoding utf8BOM
$dischargeRows | Export-Csv -LiteralPath $dischargePath -NoTypeInformation -Encoding utf8BOM
$summaryRows | Sort-Object cell_id, cycle_index, step_index | Export-Csv -LiteralPath $summaryPath -NoTypeInformation -Encoding utf8BOM

[ordered]@{
    generated_at = (Get-Date).ToString("o")
    nominal_capacity_Ah = $NominalCapacityAh
    rate_basis_power_W = $RateBasisPowerW
    rate_label_definition = "target_power_W / rate_basis_power_W; protocol-derived power rate (P)"
    segment_role_definition = "main when step capacity >= 5% nominal capacity; otherwise supplementary"
    capacity_energy_definition = "positive accumulation from the first record of each charge/discharge step"
    sources = $sourceRecords
    outputs = @(
        [IO.Path]::GetFileName($chargePath),
        [IO.Path]::GetFileName($dischargePath),
        [IO.Path]::GetFileName($summaryPath)
    )
} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $manifestPath -Encoding utf8

Write-Output $OutputDir
