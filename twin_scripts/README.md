# Generate and build twins

### Preparing Configurations

`gen_twin_dir.py` creates a new `twin` directory, and puts two copies of the spire folder into it (A and B).

`twin_scripts/gen_twin.py` takes a json file for a spire 3.0 supported topology and copies the configuration into different configurations with port and ip paddings. It also copies the docker container activation python script `run_client_twin.py` and `run_replical_twin.py` into the twins, creates a `docker-compose.yml` into `twin/spireA/scripts/conf/conf_twins`, and a `Dockerfile` in the `twin` directory.

### Running Twins

Run from `spire` (project root):

Follow the docker commands below:
```bash
python3 twin_scripts/gen_twin.py <config_file_path> <num_twins>
docker build -f twins/Dockerfile -t spire-img twins
docker compose -f twins/spireA/scripts/conf/conf_twins/docker-compose.yml --profile full up -d
```


For example:
```bash
python3 twin_scripts/gen_twin.py twin_scripts/conf_4_mod.json 2
docker build -f twins/Dockerfile -t spire-img twins
docker compose -f twins/spireA/scripts/conf/conf_twins/docker-compose.yml --profile full up -d
```

To shut down containers:

```bash
docker compose -f twins/spireA/scripts/conf/conf_twins/docker-compose.yml --profile full down
```

To clear docker build cache:

```bash
docker builder prune -a -f
```




