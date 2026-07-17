% Check COMSOL with MATLAB / LiveLink for MATLAB environment.

script_dir = fileparts(mfilename('fullpath'));
project_root = fileparts(script_dir);
logs_dir = fullfile(project_root, 'logs');

if ~exist(logs_dir, 'dir')
    mkdir(logs_dir);
end

log_file = fullfile(logs_dir, 'env_check.log');
if exist(log_file, 'file')
    delete(log_file);
end

diary(log_file);
cleanup_diary = onCleanup(@() diary('off'));

fprintf('COMSOL LiveLink environment check\n');
fprintf('Date: %s\n', datestr(now, 'yyyy-mm-dd HH:MM:SS'));
fprintf('Project root: %s\n', project_root);
fprintf('Current working directory: %s\n\n', pwd);

comsol_info = setup_comsol_livelink_path();

fprintf('COMSOL root: %s\n', comsol_info.root);
fprintf('COMSOL mli path: %s\n', comsol_info.mli_path);
fprintf('COMSOL bin path: %s\n', comsol_info.bin_path);
fprintf('COMSOL path setup status: %s\n\n', comsol_info.status);

fprintf('MATLAB path after COMSOL setup:\n%s\n\n', path);

required_functions = {'mphstart', 'mphload', 'mphsave', 'mphinterp', 'mphglobal'};
availability = struct();
all_available = strcmp(comsol_info.status, 'success');

fprintf('Required LiveLink functions:\n');
for i = 1:numel(required_functions)
    fn = required_functions{i};
    location = which(fn);
    availability.(fn) = location;

    if isempty(location)
        all_available = false;
        fprintf('  [missing] %s\n', fn);
    else
        fprintf('  [ok] %s -> %s\n', fn, location);
    end
end
fprintf('\n');

try
    import com.comsol.model.*
    import com.comsol.model.util.*
    fprintf('[ok] COMSOL Java packages are importable from MATLAB.\n');
catch ME
    all_available = false;
    fprintf('[failed] COMSOL Java package import failed.\n');
    fprintf('%s\n', getReport(ME, 'extended', 'hyperlinks', 'off'));
end

server_info = struct();
server_info.status = 'skipped';
server_info.port = NaN;
server_info.pid = NaN;
server_info.version = '';

if all_required_functions_available(required_functions)
    server_info = verify_comsol_server_connection(comsol_info);
    if ~strcmp(server_info.status, 'success')
        all_available = false;
    end
else
    all_available = false;
    fprintf('[skipped] COMSOL server connection check because required LiveLink functions are missing.\n');
end

models_dir = fullfile(project_root, 'models');
mph_files = dir(fullfile(models_dir, '*.mph'));

if isempty(mph_files)
    fprintf('\nNo .mph baseline model found under: %s\n', models_dir);
else
    test_model = fullfile(mph_files(1).folder, mph_files(1).name);
    fprintf('\nTesting mphload with first model: %s\n', test_model);

    try
        model = mphload(test_model);
        fprintf('[ok] mphload succeeded.\n');

        try
            tags = get_model_tags(model);
            fprintf('Model tags: %s\n', strjoin(tags, ', '));
        catch ME_tags
            fprintf('[warning] Could not read model tags: %s\n', ME_tags.message);
        end

        try
            com.comsol.model.util.ModelUtil.remove(model.tag());
        catch
        end
    catch ME
        all_available = false;
        fprintf('[failed] mphload failed.\n');
        fprintf('%s\n', getReport(ME, 'extended', 'hyperlinks', 'off'));
    end
end

if all_available
    fprintf('\nEnvironment check result: success\n');
else
    fprintf('\nEnvironment check result: failed\n');
    fprintf('If LiveLink functions are missing, check MATLAB path, COMSOL installation, license, and COMSOL server connection.\n');
end

env_check_result = struct();
env_check_result.status = ternary(all_available, 'success', 'failed');
env_check_result.log_file = log_file;
env_check_result.comsol = comsol_info;
env_check_result.server = server_info;
env_check_result.required_functions = availability;
env_check_result.models_found = numel(mph_files);

assignin('base', 'env_check_result', env_check_result);

function info = setup_comsol_livelink_path()
info = struct();
info.status = 'failed';
info.root = '';
info.mli_path = '';
info.bin_path = '';

existing_mphstart = which('mphstart');
if ~isempty(existing_mphstart)
    info.mli_path = fileparts(existing_mphstart);
    info.root = fileparts(info.mli_path);
    info.bin_path = fullfile(info.root, 'bin', 'win64');
    info.status = 'success';
    return
end

roots = candidate_comsol_roots();
for i = 1:numel(roots)
    root = roots{i};
    mli_path = fullfile(root, 'mli');
    if exist(fullfile(mli_path, 'mphstart.m'), 'file') || exist(fullfile(mli_path, 'mphstart.p'), 'file')
        addpath(mli_path);
        info.root = root;
        info.mli_path = mli_path;
        info.bin_path = fullfile(root, 'bin', 'win64');
        info.status = 'success';
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

function tf = all_required_functions_available(required_functions)
tf = true;
for i = 1:numel(required_functions)
    if isempty(which(required_functions{i}))
        tf = false;
        return
    end
end
end

function server_info = verify_comsol_server_connection(comsol_info)
server_info = struct();
server_info.status = 'failed';
server_info.port = NaN;
server_info.pid = NaN;
server_info.version = '';

if isempty(comsol_info.root)
    fprintf('[failed] COMSOL root is empty; cannot start mphserver.\n');
    return
end

try
    fprintf('\nStarting COMSOL mphserver for connection check...\n');
    [port, pid] = mphstartcomsolmphserver( ...
        'comsolpath', comsol_info.root, ...
        'hide', 'on', ...
        'silent', 'on', ...
        'timeout', 90);

    server_info.port = port;
    server_info.pid = pid;
    fprintf('[ok] mphserver started. port=%d, pid=%d\n', port, pid);

    mphstart(port);
    import com.comsol.model.util.*
    server_info.version = char(ModelUtil.getComsolVersion());
    server_info.status = 'success';
    fprintf('[ok] MATLAB connected to COMSOL server: %s\n', server_info.version);

    try
        ModelUtil.disconnect;
    catch
    end
catch ME
    fprintf('[failed] COMSOL server connection check failed.\n');
    fprintf('%s\n', getReport(ME, 'extended', 'hyperlinks', 'off'));
end
end

function out = ternary(condition, true_value, false_value)
if condition
    out = true_value;
else
    out = false_value;
end
end

function tags = get_model_tags(model)
tags = {};
try
    raw_tags = model.tags();
    tags = cell(raw_tags);
catch
    try
        raw_tags = model.tags;
        tags = cell(raw_tags);
    catch
        tags = {};
    end
end
end
