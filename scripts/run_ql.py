import os
import json
import shutil

# Default directories, can be overridden by environment variables
SCRIPT_DIR = os.getenv('CODEQL_SCRIPTS_DIR', '/workspace/scripts')
QUERIES_DIR = os.getenv('CODEQL_QUERIES_DIR', '/workspace/queries')
OUTPUTS_DIR = os.getenv('CODEQL_OUTPUTS_DIR', '/workspace/outputs')
DB_DIR = os.getenv('CODEQL_DB_DIR', '/workspace/db')
SRC_ROOT = os.getenv('CODEQL_SRC_ROOT', '/workspace/src')


def print_message(str, flush=True):
    print("RUNQL: " + str, end='\n', flush=flush)


def create_database(name, config):
    print_message("Creating CodeQL database...", flush=True)
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)

    db_name = name
    db_path = os.path.join(DB_DIR, name)
    db_lang = config['language']
    db_command = config.get('command', None)
    src_path = os.path.join(SRC_ROOT, config['srcPath'])
    
    configure_path = os.path.join(src_path, 'configure')
    if os.path.isfile(configure_path):
        # 转换整个源码目录下的脚本文件的行结束符
        # print_message(f"Converting line endings for scripts in {src_path}...", flush=True)
        # 使用sed命令强制转换src_path下所有文件的行结束符
        # os.system(f"find {src_path} -type f -exec sed -i 's/\\r$//' {{}} + 2>/dev/null || true")

        print_message(f"Running configure script at {configure_path}...", flush=True)
        # 确保configure脚本有执行权限
        os.system(f"chmod +x {configure_path}")
        # 运行configure脚本
        result = os.system(f"cd {src_path} && ./configure")
        if result != 0:
            print_message(f"Configure script failed with exit code {result}", flush=True)

    if db_lang not in ['cpp', 'java', 'python', 'go', 'javascript', 'typescript']:
        raise ValueError(f"Unsupported language: {db_lang}. Supported languages are: cpp, java, python, javascript, typescript.")
    if db_lang in ['cpp', 'java', 'go']:
        if db_command is None:
            raise ValueError(f"'command' is required for {db_lang} language.")
        else:
            status = os.system(f"codeql database create {db_path} \
                      --language={db_lang} \
                      --command='{db_command}' \
                      --source-root={src_path}")
            if status != 0:
                raise RuntimeError(f"Failed to create database for {db_name} with command: {db_command}")
    else:
        status = os.system(f"codeql database create {db_path} \
                  --language={db_lang} \
                  --source-root={src_path}")
        if status != 0:
            raise RuntimeError(f"Failed to create database for {db_name}")

    os.system("cd /workspace")


def install_packages(name: str, config):
    queries_path = os.path.join(QUERIES_DIR, name)
    db_lang = config['language']
    
    if not os.path.exists(queries_path):
        os.makedirs(queries_path)
    with open(os.path.join(queries_path, 'qlpack.yml'), 'w') as f:
        f.write(f"name: {name.lower()}\ndependencies:\n  codeql/{db_lang}-all: \"*\"\n")

    print_message("Installing CodeQL packages...", flush=True)
    status = os.system(f"codeql pack install {queries_path}")
    if status != 0:
        raise RuntimeError("Failed to install CodeQL packages.")


def run_ql(name):
    print_message("Running CodeQL queries...", flush=True)

    db_path = os.path.join(DB_DIR, name)
    output_path = os.path.join(OUTPUTS_DIR, f'{name}_results.csv')
    query_path = os.path.join(QUERIES_DIR, name)

    status = os.system(f"codeql database analyze {db_path} {query_path} --format=csv --output={output_path} --rerun")

    if status != 0:
        raise RuntimeError("Failed to run CodeQL queries.")

    print_message(f"CodeQL analysis completed. Results are saved in {output_path}", flush=True)


def create_and_run_database(name, config, config_lock, first_build):
    if first_build or config_lock.get('config') != config or config.get('rebuild', False):
        print_message("Configuration has changed or first build, resetting the database and lock file.", flush=True)
        if not first_build:
            db_name = name
            db_path = os.path.join(DB_DIR, db_name)
            print_message(f"Removing old database at {db_path}", flush=True)
            if os.path.exists(db_path):
                shutil.rmtree(db_path)

        # Reset the lock file
        first_build = True
        config['rebuild'] = False
        config['enabled'] = True
        config_lock['config'] = config.copy()
        config_lock['installed'] = False
        config_lock['build'] = False

    if first_build or not config_lock['build']:
        try:
            if not first_build:
                db_name = name
                db_path = os.path.join(DB_DIR, db_name)
                if os.path.exists(db_path):
                    shutil.rmtree(db_path)

            create_database(name, config)
            config_lock['build'] = True
        except Exception as e:
            print_message(f"Error creating database: {e}", flush=True)
            return

    if first_build or not config_lock['installed']:
        try:
            install_packages(name, config)
            config_lock['installed'] = True
            print_message("CodeQL packages installed successfully.", flush=True)
            print_message(f"You can write your own queries in queries/{name}.", flush=True)
            print_message(f"If you want to rebuild the database, set 'rebuild' to true in 'dbconfig.json'.", flush=True)
        except Exception as e:
            print_message(f"Error installing packages: {e}", flush=True)
            return

    try:
        run_ql(name)
    except Exception as e:
        print_message(f"Error running QL: {e}", flush=True)
        return


def for_each_config():
    with (open(os.path.join(QUERIES_DIR, 'dbconfig.json'), 'r+') as config_file,
        open(os.path.join(SCRIPT_DIR, 'dbconfig-lock.json'), 'r+') as lock_file):
        try:
            configs = json.load(config_file)
        except json.JSONDecodeError as e:
            print_message(f"Error decoding JSON from dbconfig.json: {e}", flush=True)
            return
        
        try:
            configs_lock = json.load(lock_file)
        except json.JSONDecodeError as e:
            print_message("dbconfig-lock.json has been corrupted, initializing an empty lock file.", flush=True)
            configs_lock = {}

        for name, config in configs.items():
            if not config.get("enabled", True):
                print_message(f"Configuration '{name}' is disabled, skipping.", flush=True)
                continue

            if (config.get('language') is None or config.get('srcPath') is None):
                print_message("Configuration must contain a 'language', 'srcPath' field.")
                continue

            if configs_lock.get(name) is None:
                print_message(f"Initializing Configuration '{name}'", flush=True)
                configs_lock[name] = {}
                config_lock = configs_lock[name]
                first_build = True
            else:
                config_lock = configs_lock[name]
                first_build = False

            create_and_run_database(name, config, config_lock, first_build)

        del_keys = []
        for name, config in configs_lock.items():
            if name not in configs:
                print_message(f"Configuration '{name}' is not in dbconfig.json, removing from lock file and database.", flush=True)
                db_name = name
                db_path = os.path.join(DB_DIR, db_name)
                if os.path.exists(db_path):
                    shutil.rmtree(db_path)
                del_keys.append(name)

        for key in del_keys:
            del configs_lock[key]

        lock_file.seek(0)
        json.dump(configs_lock, lock_file, indent=4)
        lock_file.truncate()

        config_file.seek(0)
        json.dump(configs, config_file, indent=4)
        config_file.truncate()


def create_files():
    config_path = os.path.join(QUERIES_DIR, 'dbconfig.json')
    if not os.path.exists(config_path):
        print_message("""Configuration file does not exist. Please create it.
              Example configuration can be found in dbconfig.json
              Please put it in queries directory.
              """, flush=True)
        return
    
    lock_path = os.path.join(SCRIPT_DIR, 'dbconfig-lock.json')
    if not os.path.exists(lock_path):
        with open(lock_path, 'w') as f:
            f.write('{}') 


if __name__ == "__main__":
    create_files()
    for_each_config()