source ~/.bash_profile

echo "[$(date +'%Y-%m-%d %H:%M:%S')] main_start.sh"

conda activate premium

BASE=fexchange

PID=$(ps -ef | grep main.py | grep ${BASE} | grep -v grep | awk {'print $2'})

## PID 값이존재하지 않을 때
if [ -z $PID ]
then
        echo "Start main.py"

	sleep 1 
	nohup python3 /root/${BASE}/main.py > /dev/null 2>&1 &
	
	sleep 1
        ps -ef | grep main.py | grep ${BASE} | grep -v grep
else
        echo "main.py is running"
fi
