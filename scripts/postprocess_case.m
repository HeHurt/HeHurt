% Postprocess the latest COMSOL with MATLAB run folder.

script_dir = fileparts(mfilename('fullpath'));
project_root = fileparts(script_dir);
runs_dir = fullfile(project_root, 'runs');
results_dir = fullfile(project_root, 'results');

if ~exist(results_dir, 'dir')
    mkdir(results_dir);
end

latest_run = find_latest_run(runs_dir);

if isempty(latest_run)
    fprintf('No run folder found under: %s\n', runs_dir);
    postprocess_result = struct('status', 'failed', 'message', 'No run folder found.');
    assignin('base', 'postprocess_result', postprocess_result);
    return
end

fprintf('Latest run: %s\n', latest_run);

metrics_file = fullfile(latest_run, 'metrics.csv');
plots_dir = fullfile(latest_run, 'plots');
data_dir = fullfile(latest_run, 'exported_data');
[~, run_name] = fileparts(latest_run);
target_dir = fullfile(results_dir, run_name);

if ~exist(target_dir, 'dir')
    mkdir(target_dir);
end

postprocess_result = struct();
postprocess_result.status = 'success';
postprocess_result.run_dir = latest_run;
postprocess_result.results_dir = target_dir;
postprocess_result.missing = {};

if exist(metrics_file, 'file')
    fprintf('\nMetrics:\n');
    metrics_text = read_text_with_dlp_fallback(metrics_file);
    fprintf('%s\n', metrics_text);
    write_text_with_python_fallback(fullfile(target_dir, 'metrics.csv'), metrics_text);
else
    fprintf('Missing metrics.csv: %s\n', metrics_file);
    postprocess_result.missing{end + 1} = 'metrics.csv';
end

if exist(plots_dir, 'dir') && has_files(plots_dir)
    copyfile(plots_dir, fullfile(target_dir, 'plots'));
    fprintf('Copied plots to results.\n');
else
    fprintf('No plots found under: %s\n', plots_dir);
    postprocess_result.missing{end + 1} = 'plots';
end

if exist(data_dir, 'dir') && has_files(data_dir)
    copyfile(data_dir, fullfile(target_dir, 'exported_data'));
    fprintf('Copied exported data to results.\n');
else
    fprintf('No exported data found under: %s\n', data_dir);
    postprocess_result.missing{end + 1} = 'exported_data';
end

if ~isempty(postprocess_result.missing)
    postprocess_result.status = 'partial';
    fprintf('\nPostprocess completed with missing items: %s\n', strjoin(postprocess_result.missing, ', '));
else
    fprintf('\nPostprocess completed successfully.\n');
end

assignin('base', 'postprocess_result', postprocess_result);

function latest_run = find_latest_run(runs_dir)
latest_run = '';

if ~exist(runs_dir, 'dir')
    return
end

items = dir(runs_dir);
items = items([items.isdir]);
items = items(~ismember({items.name}, {'.', '..'}));

if isempty(items)
    return
end

[~, idx] = max([items.datenum]);
latest_run = fullfile(items(idx).folder, items(idx).name);
end

function tf = has_files(folder)
items = dir(folder);
items = items(~[items.isdir]);
tf = ~isempty(items);
end

function text = read_text_with_dlp_fallback(file_path)
text = fileread(file_path);
if starts_with_tsd_header(text)
    [status, out] = run_python_text_io('read', file_path, '');
    if status ~= 0
        error('postprocess_case:DlpReadFailed', 'DLP fallback read failed for %s: %s', file_path, out);
    end
    text = out;
end
end

function write_text_with_python_fallback(file_path, text)
[status, out] = run_python_text_io('write', file_path, text);
if status == 0
    return
end

warning('postprocess_case:PythonWriteFailed', 'Python write fallback failed: %s. Falling back to MATLAB fopen.', out);
fid = fopen(file_path, 'w');
if fid < 0
    error('postprocess_case:FileOpenFailed', 'Could not open file for writing: %s', file_path);
end
cleanup_file = onCleanup(@() fclose(fid));
fprintf(fid, '%s', text);
end

function tf = starts_with_tsd_header(text)
prefix_len = min(numel(text), 64);
tf = contains(text(1:prefix_len), '%TSD-Header-###%');
end

function [status, out] = run_python_text_io(mode, file_path, text)
script_path = [tempname, '.py'];
temp_text_path = [tempname, '.txt'];

cleanup_script = onCleanup(@() delete_if_exists(script_path));
cleanup_text = onCleanup(@() delete_if_exists(temp_text_path));

if strcmp(mode, 'write')
    fid = fopen(temp_text_path, 'w');
    if fid < 0
        status = 1;
        out = sprintf('Could not open temp file: %s', temp_text_path);
        return
    end
    cleanup_file = onCleanup(@() fclose(fid));
    fprintf(fid, '%s', text);
    clear cleanup_file
end

fid = fopen(script_path, 'w');
if fid < 0
    status = 1;
    out = sprintf('Could not open temp Python script: %s', script_path);
    return
end
cleanup_file = onCleanup(@() fclose(fid));

if strcmp(mode, 'read')
    fprintf(fid, 'from pathlib import Path\n');
    fprintf(fid, 'import sys\n');
    fprintf(fid, 'p = Path(r"""%s""")\n', file_path);
    fprintf(fid, 'sys.stdout.write(p.read_text(encoding="utf-8", errors="replace"))\n');
else
    fprintf(fid, 'from pathlib import Path\n');
    fprintf(fid, 'src = Path(r"""%s""")\n', temp_text_path);
    fprintf(fid, 'dst = Path(r"""%s""")\n', file_path);
    fprintf(fid, 'dst.parent.mkdir(parents=True, exist_ok=True)\n');
    fprintf(fid, 'dst.write_text(src.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")\n');
end
clear cleanup_file

[status, out] = system(sprintf('python "%s"', script_path));
end

function delete_if_exists(path_value)
if exist(path_value, 'file')
    delete(path_value);
end
end
