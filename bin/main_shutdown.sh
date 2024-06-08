source ~/.bash_profile

echo "[$(date +'%Y-%m-%d %H:%M:%S')] main_stop.sh"

BASE=fexchange

PID=$(ps -ef | grep main.py | grep ${BASE} | grep -v grep | awk {'print $2'})


## PID 값이 존재할 때
if [ -n $PID ]
then
	echo "Stop main.py"
	kill -9 ${PID}
	ps -ef | grep main.py | grep ${BASE} | grep -v grep
else
	echo "main.py is not running"
fi
