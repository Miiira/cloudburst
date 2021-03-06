import time
import struct
import logging
from cloudburst.client.client import CloudburstConnection
# change this every time the cluster restarts
dc = CloudburstConnection('a745ff89e3f21440ca8cf5a920036179-1240797621.us-east-1.elb.amazonaws.com', '75.101.215.70') # function_elb, driver_node_ip

#PATH_RVF = 0xb11b0c45
#PATH_RVD = PATH_RVF + 0x100

def deserializePath(buf):
    headerSize = 4+4+8+4
    wpSize = 8*8

    tp, size, cost, solveTimeMillis = struct.unpack_from('>LLdL', buf, 0)
    print(tp, size, cost, solveTimeMillis)
    nWaypoints = (len(buf) - headerSize) / wpSize
    print(nWaypoints)

    waypoints = []
    for t in range(int(nWaypoints)):
    	waypoints.append(struct.unpack_from('>8d', buf, headerSize + t*wpSize))

    return waypoints


def mpl_anna(cloudburst, anna_routing_address, execution_id): # function to register
	import os, subprocess
	local_ip = ip = os.popen("ifconfig eth0 | grep 'inet addr:' | grep -v '127.0.0.1' | cut -d: -f2 | awk '{ print $1 }'").read().strip()
	thread_id = str(1 + int(os.popen("echo $THREAD_ID").read().strip()))
	os.environ["OMP_NUM_THREADS"] = "1"
	os.environ["LD_LIBRARY_PATH"] = "/root/local/lib:/root/local/lib64:/usr/local/lib"
	os.environ["PKG_CONFIG_PATH"] = "/root/local/share/pkgconfig:/root/local/lib64/pkgconfig"
	os.environ["PI"] = "3.141592653589793"
	os.environ["PI_2"] = "1.570796326794897"

	#execution_command = '/hydro/mplambda/build/mpl_lambda_pseudo --scenario se3 --algorithm cforest --coordinator "$COORDINATOR" --jobs 10 --env se3/Twistycool_env.dae --robot se3/Twistycool_robot.dae --start 0,1,0,0,270,160,-200 --goal 0,1,0,0,270,160,-400 --min 53.46,-21.25,-476.86 --max 402.96,269.25,-91.0 --time-limit 60 --check-resolution 0.1 --anna_address ' + anna_address + ' --local_ip ' + local_ip + ' --execution_id ' + execution_id + ' --thread_id ' + thread_id
	execution_command = '/hydro/mplambda/build/mpl_lambda_pseudo --scenario fetch --algorithm cforest --coordinator "$COORDINATOR" --jobs 10 --env AUTOLAB.dae --env-frame=0.38,-0.90,0.00,0,0,-$PI_2 --goal=-1.07,0.16,0.88,0,0,0 --goal-radius=0.01,0.01,0.01,0.01,0.01,$PI --start=0.1,$PI_2,$PI_2,0,$PI_2,0,$PI_2,0 --time-limit 60 --check-resolution 0.01 --anna_address ' + anna_routing_address + ' --local_ip ' + local_ip + ' --execution_id ' + execution_id + ' --thread_id ' + thread_id
	result = subprocess.run([execution_command], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)

	print("result", result, "111")
	print("thread_id", thread_id, "222")

	log.info("result" + result + "333333")
	log.info("thread_id" + thread_id + "555555")

	return result, thread_id

cloud_func = dc.register(mpl_anna, 'mpl_anna')
# wait for 1 second for the registration process to fully finish
time.sleep(1)
f = open("result.txt", "w")

run = 0
# run the same experiment 24 times and take average
while run <=1:
	time.sleep(1)
	run += 1
	f.write('T' + str(run) + '\n')
	print('T' + str(run))
	solution_key = ('solution_key_' + str(run)) # deferentiate keys
	future_list = []
	for i in range(2): # parallely run. 10 is the number of function requests. TODO: spin up more nodes
		future_list.append(cloud_func('a6c92813443ed402dab1985921470e92-1252235988.us-east-1.elb.amazonaws.com', solution_key)) # routing_elb
	count = 1
	print("[[",future_list,"]]")
	for future in future_list:
		print(count)
		count += 1
		print('object id is %s' % future.obj_id)
	start = time.time()
	result = None
	while result is None:
		# print("dc.kvs_client", dc.kvs_client, "||")
		print("&$", dc.kvs_client.get(solution_key), "&$")
		print("|$$$", type(dc.kvs_client.get(solution_key)[solution_key].payload.peekitem(0)), "|")
		if dc.kvs_client.get(solution_key)[solution_key] is not None: 
			print("heyyyy  dc.kvs_client.get(solution_key)[solution_key] is not None")
			result = dc.kvs_client.get(solution_key)[solution_key].payload.peekitem(0)
		if time.time() - start > 60: # terminate after 60 sec 
			break
	if result is None:
		print('no solution found')
		continue
	first = time.time()
	output = '%s, %s' % (first-start, result[0])
	print(output)
	f.write(output + '\n')
	#print(result.priority)
	while True:
		new_result = dc.kvs_client.get(solution_key)[solution_key].payload.peekitem(0)
		if not new_result is None and new_result[0] < result[0]: # priority is proportional to path length. the lower the better
			# top K -> pick shortest 
			result = new_result
			output = '%s, %s' % (time.time()-start, result[0])
			print(output)
			f.write(output + '\n')
			#print(result.priority)
		current_time = time.time()
		if current_time - start > 1: # run for 60 seconds
			break
	print('getting results')
	for future in future_list:
		print(",,,,,,,")
		future.get()

	print('printing waypoints')
	print(deserializePath(result[1]))
f.close()

