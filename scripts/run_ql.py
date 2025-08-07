import os
import json
import shutil

SCRIPT_DIR = '/workspace/scripts'
QUERIES_DIR = '/workspace/queries'
OUTPUTS_DIR = '/workspace/outputs'
DB_DIR = '/workspace/db'
SRC_ROOT = '/workspace/src'

def run_ql(config):
    print("Running CodeQL queries...", flush=True)

    db_path = os.path.join(DB_DIR, config['name'])
    output_path = os.path.join(OUTPUTS_DIR, f'{config["name"]}_results.csv')

    status = os.system(f"cd {os.path.join(SRC_ROOT, config['srcPath'])} && codeql database analyze {db_path} {QUERIES_DIR} --format=csv --output={output_path}")

    if status != 0:
        raise RuntimeError("Failed to run CodeQL queries.")

    os.system("cd /")  # Reset working directory

    print(f"CodeQL analysis completed. Results are saved in {output_path}", flush=True)

def create_database(config):
    print("Creating CodeQL database...", flush=True)

    db_name = config['name']
    db_path = config['srcPath']
    db_lang = config['language']
    db_command = config.get('command', None)

    if db_lang not in ['cpp', 'java', 'python', 'go', 'javascript', 'typescript']:
        raise ValueError(f"Unsupported language: {db_lang}. Supported languages are: cpp, java, python, javascript, typescript.")
    if db_lang in ['cpp', 'java', 'go']:
        if db_command is None:
            raise ValueError(f"'command' is required for {db_lang} language.")
        else:
            status = os.system(f"codeql database create {os.path.join(DB_DIR, db_name)} \
                      --language={db_lang} \
                      --command='{db_command}' \
                      --source-root={os.path.join(SRC_ROOT, db_path)}")
            if status != 0:
                raise RuntimeError(f"Failed to create database for {db_name} with command: {db_command}")
    else:
        status = os.system(f"codeql database create {os.path.join(DB_DIR, db_name)} \
                  --language={db_lang} \
                  --source-root={os.path.join(SRC_ROOT, db_path)}")
        if status != 0:
            raise RuntimeError(f"Failed to create database for {db_name}")

def install_packages(config):
    queries_path = os.path.join(QUERIES_DIR, config['name'])
    if not os.path.exists(queries_path):
        os.makedirs(queries_path)
    with open(os.path.join(queries_path, 'qlpack.yml'), 'w') as f:
        f.write(f"name: test\ndependencies:\n  codeql/{config['language']}-all: \"*\"\n")

    print("Installing CodeQL packages...", flush=True)
    status = os.system(f"codeql pack install {queries_path}")
    if status != 0:
        raise RuntimeError("Failed to install CodeQL packages.")

def main():
    with (open(os.path.join(QUERIES_DIR, 'dbconfig.json'), 'r+') as config_file,
        open(os.path.join(SCRIPT_DIR, 'dbconfig-lock.json'), 'r+') as lock_file):
        try:
            config = json.load(config_file)
            if (config.get('name') is None or config.get('language') is None or config.get('srcPath') is None):
                raise ValueError("Configuration must contain a 'name', 'language', and 'srcPath' field.")
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from dbconfig.json: {e}", flush=True)
            return
        
        first_build = False
        try:
            config_lock = json.load(lock_file)
        except json.JSONDecodeError:
            first_build = True
            config_lock = {}

        if first_build or config_lock.get('config') != config or config.get('rebuild', False):
            print("Configuration has changed or first build, resetting the database and lock file.", flush=True)
            if not first_build:
                db_name = config_lock["config"]["name"]
                db_path = os.path.join(DB_DIR, db_name)
                print(f"Removing old database at {db_path}", flush=True)
                if os.path.exists(db_path):
                    shutil.rmtree(db_path)

            # Reset the lock file
            first_build = True
            config_lock['config'] = config.copy()
            config_lock['installed'] = False
            config_lock['build'] = False
            config['rebuild'] = False
            config_lock['config']['rebuild'] = False
            lock_file.seek(0)
            json.dump(config_lock, lock_file)
            lock_file.truncate()
            config_file.seek(0)
            json.dump(config, config_file, indent=4)
            config_file.truncate()

        if first_build or config_lock['build'] == False:
            try:
                if not first_build:
                    db_name = config_lock["config"]["name"]
                    db_path = os.path.join(DB_DIR, db_name)
                    if os.path.exists(db_path):
                        shutil.rmtree(db_path)

                create_database(config)
                config_lock['build'] = True
            except Exception as e:
                print(f"Error creating database: {e}", flush=True)
                return
            finally:
                lock_file.seek(0)
                json.dump(config_lock, lock_file)
                lock_file.truncate()

        if first_build or config_lock['installed'] == False:
            try:
                install_packages(config)
                config_lock['installed'] = True
                print("CodeQL packages installed successfully.", flush=True)
                print(f"You can write your own queries in queries/{config['name']}.", flush=True)
                print(f"If you want to rebuild the database, set 'rebuild' to true in 'dbconfig.json'.", flush=True)
            except Exception as e:
                print(f"Error installing packages: {e}", flush=True)
                return
            finally:
                lock_file.seek(0)
                json.dump(config_lock, lock_file)
                lock_file.truncate()
                
        try:
            run_ql(config)
        except Exception as e:
            print(f"Error running QL: {e}", flush=True)
            return

if __name__ == "__main__":
    main()