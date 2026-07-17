% Run one minimal COMSOL with MATLAB case and record all outputs.
%
% Optional input from caller workspace:
%   config.case_name
%   config.model_path
%   config.study_tag
%
% Example:
%   config.case_name = "baseline";
%   run('scripts/run_case.m');

if ~exist('config', 'var') || ~isstruct(config)
    config = struct();
end

result = run_case_impl(config);
assignin('base', 'result', result);

function result = run_case_impl(config)
script_file = mfilename('fullpath');
script_dir = fileparts(script_file);
project_root = fileparts(script_dir);

config = normalize_config(config, project_root);
config = setup_comsol_livelink_path(config);
ensure_dir(config.runs_dir);
ensure_dir(config.logs_dir);
ensure_dir(config.models_dir);

timestamp = datestr(now, 'yyyymmdd_HHMMSS');
run_name = sprintf('%s_%s', timestamp, sanitize_name(config.case_name));
run_dir = fullfile(config.runs_dir, run_name);
plots_dir = fullfile(run_dir, 'plots');
data_dir = fullfile(run_dir, 'exported_data');

ensure_dir(run_dir);
ensure_dir(plots_dir);
ensure_dir(data_dir);

config.run_dir = run_dir;
config.plots_dir = plots_dir;
config.exported_data_dir = data_dir;

write_json(fullfile(run_dir, 'config.json'), config);

log_file = fullfile(run_dir, 'run.log');
diary(log_file);
cleanup_diary = onCleanup(@() diary('off'));

fprintf('COMSOL LiveLink run case\n');
fprintf('Date: %s\n', datestr(now, 'yyyy-mm-dd HH:MM:SS'));
fprintf('Run directory: %s\n', run_dir);
fprintf('Script: %s\n\n', script_file);

result = struct();
result.status = 'failed';
result.case_name = config.case_name;
result.run_dir = run_dir;
result.log_file = log_file;
result.error_report_file = fullfile(run_dir, 'error_report.txt');
result.metrics_file = fullfile(run_dir, 'metrics.csv');
result.model_snapshot = fullfile(run_dir, 'model_snapshot.mph');
result.elapsed_s = NaN;
result.error_category = '';
result.error_message = '';
result.fix_suggestion = '';
result.comsol_root = config.comsol_root;
result.comsol_version = '';
result.comsol_server_port = '';

t_start = tic;
model = [];
server_connected = false;

try
    model_path = select_model_path(config);

    if isempty(model_path)
        exported_scripts = dir(fullfile(config.models_dir, '*.m'));
        result.error_category = 'Missing baseline model issue';
        result.error_message = sprintf('No .mph baseline model found under %s.', config.models_dir);
        result.fix_suggestion = 'Provide a baseline .mph file, a COMSOL Desktop exported .m file, or complete modeling requirements.';

        if ~isempty(exported_scripts)
            names = string({exported_scripts.name});
            result.fix_suggestion = sprintf('%s Exported .m files exist under models/: %s. Set config.model_script_path after confirming which file to use.', result.fix_suggestion, strjoin(names, ', '));
        end

        fprintf('[failed] %s\n', result.error_message);
        fprintf('Suggestion: %s\n', result.fix_suggestion);
        result.elapsed_s = toc(t_start);
        write_text(result.error_report_file, format_missing_model_report(result, config));
        write_metrics(result.metrics_file, result);
        append_lesson(config.logs_dir, script_file, '', result, 'Baseline model was not available.', 'No fix applied in this run.', 'Waiting for user-provided model or modeling requirements.', result.fix_suggestion);
        return
    end

    result.model_path = model_path;
    server_info = connect_comsol_server(config);
    server_connected = true;
    result.comsol_version = server_info.version;
    result.comsol_server_port = num2str(server_info.port);

    fprintf('Loading model: %s\n', model_path);
    model = mphload(model_path);
    fprintf('[ok] Model loaded.\n');

    study_tag = select_study_tag(model, config);
    if isempty(study_tag)
        error('run_case:NoStudyFound', 'No study tag was found. Provide config.study_tag or add a study to the baseline model.');
    end

    result.study_tag = study_tag;
    fprintf('Running study: %s\n', study_tag);
    model.study(study_tag).run;
    fprintf('[ok] Study finished.\n');

    fprintf('Saving model snapshot: %s\n', result.model_snapshot);
    mphsave(model, result.model_snapshot);

    result.status = 'success';
    result.elapsed_s = toc(t_start);
    result.error_category = '';
    result.error_message = '';
    result.fix_suggestion = '';

    write_text(result.error_report_file, sprintf('No error.\n'));
    write_metrics(result.metrics_file, result);
    fprintf('[ok] Metrics saved: %s\n', result.metrics_file);
catch ME
    result.status = 'failed';
    result.elapsed_s = toc(t_start);
    result.error_message = ME.message;
    result.error_category = classify_error(ME);
    result.fix_suggestion = suggest_fix(result.error_category);

    full_report = getReport(ME, 'extended', 'hyperlinks', 'off');
    fprintf('[failed] %s\n', ME.message);
    fprintf('Error category: %s\n', result.error_category);
    fprintf('Suggestion: %s\n', result.fix_suggestion);
    fprintf('%s\n', full_report);

    comsol_errors = '';
    try
        comsol_errors = evalc('mphshowerrors(model)');
    catch
    end

    if ~isempty(comsol_errors)
        full_report = sprintf('%s\n\nCOMSOL errors:\n%s\n', full_report, comsol_errors);
    end

    try
        if ~isempty(model)
            failed_snapshot = fullfile(run_dir, 'failed_model_snapshot.mph');
            mphsave(model, failed_snapshot);
            result.model_snapshot = failed_snapshot;
        end
    catch ME_save
        full_report = sprintf('%s\n\nFailed to save model snapshot:\n%s\n', full_report, ME_save.message);
    end

    write_text(result.error_report_file, full_report);
    write_metrics(result.metrics_file, result);
    append_lesson(config.logs_dir, script_file, get_field(result, 'model_path', ''), result, result.error_message, 'Not fixed during this automated run.', 'Failed. See run folder error_report.txt.', result.fix_suggestion);
end

if server_connected
    try
        import com.comsol.model.util.*
        ModelUtil.disconnect;
        fprintf('[ok] Disconnected from COMSOL server.\n');
    catch
    end
end

fprintf('\nRun status: %s\n', result.status);
fprintf('Elapsed seconds: %.3f\n', result.elapsed_s);
end

function config = normalize_config(config, project_root)
if ~isfield(config, 'case_name') || isempty(config.case_name)
    config.case_name = 'case';
end

if isstring(config.case_name)
    config.case_name = char(config.case_name);
end

if ~isfield(config, 'project_root') || isempty(config.project_root)
    config.project_root = project_root;
end

config.models_dir = fullfile(config.project_root, 'models');
config.runs_dir = fullfile(config.project_root, 'runs');
config.logs_dir = fullfile(config.project_root, 'logs');

if ~isfield(config, 'model_path')
    config.model_path = '';
end

if ~isfield(config, 'study_tag')
    config.study_tag = '';
end

if ~isfield(config, 'comsol_root')
    config.comsol_root = '';
end

if ~isfield(config, 'comsol_mli_path')
    config.comsol_mli_path = '';
end

if ~isfield(config, 'comsol_bin_path')
    config.comsol_bin_path = '';
end

if ~isfield(config, 'comsol_server_port')
    config.comsol_server_port = [];
end

if ~isfield(config, 'auto_start_comsol_server')
    config.auto_start_comsol_server = true;
end

if ~isfield(config, 'comsol_server_timeout_s')
    config.comsol_server_timeout_s = 90;
end
end

function config = setup_comsol_livelink_path(config)
if ~isempty(config.comsol_root)
    mli_path = fullfile(char(config.comsol_root), 'mli');
    if exist(fullfile(mli_path, 'mphstart.m'), 'file') || exist(fullfile(mli_path, 'mphstart.p'), 'file')
        addpath(mli_path);
        config.comsol_root = char(config.comsol_root);
        config.comsol_mli_path = mli_path;
        config.comsol_bin_path = fullfile(config.comsol_root, 'bin', 'win64');
        return
    end
end

existing_mphstart = which('mphstart');
if ~isempty(existing_mphstart)
    config.comsol_mli_path = fileparts(existing_mphstart);
    config.comsol_root = fileparts(config.comsol_mli_path);
    config.comsol_bin_path = fullfile(config.comsol_root, 'bin', 'win64');
    return
end

roots = candidate_comsol_roots();
for i = 1:numel(roots)
    root = roots{i};
    mli_path = fullfile(root, 'mli');
    if exist(fullfile(mli_path, 'mphstart.m'), 'file') || exist(fullfile(mli_path, 'mphstart.p'), 'file')
        addpath(mli_path);
        config.comsol_root = root;
        config.comsol_mli_path = mli_path;
        config.comsol_bin_path = fullfile(root, 'bin', 'win64');
        return
    end
end
end

function roots = candidate_comsol_roots()
roots = {};

env_root = getenv('COMSOL_ROOT');
if ~isempty(env_root)
    roots{end + 1} = env_root;
end

roots = [roots, { ...
    'D:\Program Files\COMSOL\COMSOL64\Multiphysics', ...
    'C:\Program Files\COMSOL\COMSOL64\Multiphysics', ...
    'D:\COMSOL\COMSOL64\Multiphysics', ...
    'C:\COMSOL\COMSOL64\Multiphysics'}];
end

function server_info = connect_comsol_server(config)
required_functions = {'mphstart', 'mphload', 'mphsave', 'mphinterp', 'mphglobal', 'mphstartcomsolmphserver'};
for i = 1:numel(required_functions)
    if isempty(which(required_functions{i}))
        error('run_case:LiveLinkFunctionMissing', 'Required LiveLink function is not visible on MATLAB path: %s', required_functions{i});
    end
end

if isempty(config.comsol_root)
    error('run_case:ComsolRootMissing', 'COMSOL root could not be detected. Set config.comsol_root before running.');
end

server_info = struct();
server_info.status = 'failed';
server_info.port = NaN;
server_info.pid = NaN;
server_info.version = '';

if ~isempty(config.comsol_server_port)
    port = config.comsol_server_port;
    if ischar(port) || isstring(port)
        port = str2double(char(port));
    end
    fprintf('Connecting to existing COMSOL mphserver on port %d...\n', port);
    mphstart(port);
    server_info.port = port;
else
    if ~config.auto_start_comsol_server
        error('run_case:ComsolServerPortMissing', 'auto_start_comsol_server is false and config.comsol_server_port is empty.');
    end

    fprintf('Starting COMSOL mphserver from: %s\n', config.comsol_root);
    [port, pid] = mphstartcomsolmphserver( ...
        'comsolpath', config.comsol_root, ...
        'hide', 'on', ...
        'silent', 'on', ...
        'timeout', config.comsol_server_timeout_s);
    fprintf('[ok] mphserver started. port=%d, pid=%d\n', port, pid);

    mphstart(port);
    server_info.port = port;
    server_info.pid = pid;
end

import com.comsol.model.util.*
server_info.version = char(ModelUtil.getComsolVersion());
server_info.status = 'success';
fprintf('[ok] Connected to COMSOL server: %s\n', server_info.version);
end

function model_path = select_model_path(config)
model_path = '';

if isfield(config, 'model_path') && ~isempty(config.model_path)
    candidate = char(config.model_path);
    if exist(candidate, 'file')
        model_path = candidate;
        return
    end

    error('run_case:ModelPathMissing', 'Configured model_path does not exist: %s', candidate);
end

mph_files = dir(fullfile(config.models_dir, '*.mph'));
if ~isempty(mph_files)
    model_path = fullfile(mph_files(1).folder, mph_files(1).name);
end
end

function study_tag = select_study_tag(model, config)
study_tag = '';

if isfield(config, 'study_tag') && ~isempty(config.study_tag)
    study_tag = char(config.study_tag);
    return
end

tags = {};
try
    tags = cell(model.study.tags());
catch
    try
        tags = cell(model.study.tags);
    catch
        tags = {};
    end
end

if ~isempty(tags)
    study_tag = char(tags{1});
    return
end

try
    model.study('std1');
    study_tag = 'std1';
catch
    study_tag = '';
end
end

function category = classify_error(ME)
message = lower(ME.message);

if contains(message, 'license') || contains(message, 'path') || contains(message, 'undefined function') || contains(message, 'unrecognized function')
    category = 'Environment/path/license issue';
elseif contains(message, 'mphstart') || contains(message, 'server') || contains(message, 'connection')
    category = 'COMSOL server or MATLAB connection issue';
elseif contains(message, 'syntax') || contains(message, 'api')
    category = 'API syntax issue';
elseif contains(message, 'tag') || contains(message, 'unknown property') || contains(message, 'no study')
    category = 'Model tag or feature tag issue';
elseif contains(message, 'geometry') || contains(message, 'geom')
    category = 'Geometry build issue';
elseif contains(message, 'selection') || contains(message, 'domain') || contains(message, 'boundary') || contains(message, 'edge')
    category = 'Selection/domain/boundary ID issue';
elseif contains(message, 'unit') || contains(message, 'parameter') || contains(message, 'material')
    category = 'Material/parameter/unit issue';
elseif contains(message, 'mesh')
    category = 'Mesh issue';
elseif contains(message, 'conver') || contains(message, 'solver') || contains(message, 'singular')
    category = 'Solver/convergence issue';
elseif contains(message, 'memory') || contains(message, 'out of memory')
    category = 'Memory/performance issue';
elseif contains(message, 'export') || contains(message, 'postprocess') || contains(message, 'plot')
    category = 'Postprocessing/export issue';
else
    category = 'Unknown issue';
end
end

function suggestion = suggest_fix(category)
switch category
    case 'Environment/path/license issue'
        suggestion = 'Check MATLAB path, LiveLink installation, COMSOL license, and whether LiveLink functions are visible with which().';
    case 'COMSOL server or MATLAB connection issue'
        suggestion = 'Check COMSOL server status and LiveLink connection. Run scripts/check_env.m before re-running the case.';
    case 'API syntax issue'
        suggestion = 'Inspect a COMSOL Desktop exported .m file and use the exact generated API calls and tags.';
    case 'Model tag or feature tag issue'
        suggestion = 'Inspect model tags in the baseline .mph or exported .m file, then set config.study_tag or update script tags.';
    case 'Geometry build issue'
        suggestion = 'Run geometry build in COMSOL Desktop, check parameters and units, then export a known-good .m script.';
    case 'Selection/domain/boundary ID issue'
        suggestion = 'Use named selections or verify domain/boundary IDs from the model before applying physics or postprocessing.';
    case 'Material/parameter/unit issue'
        suggestion = 'Check parameter names, values, units, and material assignments in the baseline model.';
    case 'Mesh issue'
        suggestion = 'Validate geometry, simplify mesh settings, and test mesh generation before solving.';
    case 'Solver/convergence issue'
        suggestion = 'Check initial values, boundary conditions, mesh quality, and try a reduced/stationary diagnostic case.';
    case 'Memory/performance issue'
        suggestion = 'Reduce mesh density, exported field size, and batch scope before re-running.';
    case 'Postprocessing/export issue'
        suggestion = 'Verify dataset, plot, and result table tags. Separate postprocessing from solving.';
    otherwise
        suggestion = 'Read error_report.txt, inspect the exported COMSOL .m file, and rerun a minimal baseline case.';
end
end

function report = format_missing_model_report(result, config)
report = sprintf(['Status: %s\n' ...
    'Error category: %s\n' ...
    'Message: %s\n' ...
    'Models directory: %s\n' ...
    'Suggestion: %s\n'], ...
    result.status, result.error_category, result.error_message, config.models_dir, result.fix_suggestion);
end

function append_lesson(logs_dir, script_file, model_file, result, root_cause, fix_applied, verification_result, prevention_rule)
lessons_file = fullfile(logs_dir, 'lessons_learned.md');
ensure_dir(logs_dir);

entry = sprintf(['\n## Failure Summary\n\n' ...
    '- Date: %s\n' ...
    '- Script: %s\n' ...
    '- Model: %s\n' ...
    '- Error category: %s\n' ...
    '- Full error: %s\n' ...
    '- Root cause: %s\n' ...
    '- Fix applied: %s\n' ...
    '- Verification result: %s\n' ...
    '- Prevention rule: %s\n'], ...
    datestr(now, 'yyyy-mm-dd HH:MM:SS'), script_file, model_file, result.error_category, result.error_message, root_cause, fix_applied, verification_result, prevention_rule);

fid = fopen(lessons_file, 'a');
cleanup_file = onCleanup(@() fclose(fid));
fprintf(fid, '%s', entry);
end

function write_metrics(file_path, result)
headers = {'status', 'case_name', 'elapsed_s', 'error_category', 'error_message', 'fix_suggestion', 'run_dir', 'model_path', 'study_tag', 'model_snapshot', 'comsol_root', 'comsol_version', 'comsol_server_port'};
fid = fopen(file_path, 'w');
cleanup_file = onCleanup(@() fclose(fid));
fprintf(fid, '%s\n', strjoin(headers, ','));

values = cell(size(headers));
for i = 1:numel(headers)
    values{i} = csv_escape(get_field(result, headers{i}, ''));
end
fprintf(fid, '%s\n', strjoin(values, ','));
end

function value = get_field(s, field_name, default_value)
if isfield(s, field_name)
    value = s.(field_name);
else
    value = default_value;
end

if isnumeric(value)
    value = num2str(value);
elseif isstring(value)
    value = char(value);
elseif islogical(value)
    value = char(string(value));
elseif ~ischar(value)
    value = char(string(value));
end
end

function escaped = csv_escape(value)
value = char(value);
value = strrep(value, '"', '""');
escaped = ['"', value, '"'];
end

function write_json(file_path, data)
try
    text = jsonencode(data, 'PrettyPrint', true);
catch
    text = jsonencode(data);
end
write_text(file_path, text);
end

function write_text(file_path, text)
fid = fopen(file_path, 'w');
if fid < 0
    error('run_case:FileOpenFailed', 'Could not open file for writing: %s', file_path);
end
cleanup_file = onCleanup(@() fclose(fid));
fprintf(fid, '%s', text);
end

function ensure_dir(path_value)
if ~exist(path_value, 'dir')
    mkdir(path_value);
end
end

function name = sanitize_name(name)
name = char(name);
name = regexprep(name, '[^\w\-]+', '_');
if isempty(name)
    name = 'case';
end
end
