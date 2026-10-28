# Generate and build twins

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

To clear docker build cache:

```bash
docker builder prune -a -f
```




