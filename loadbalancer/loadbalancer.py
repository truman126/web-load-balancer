import socket
import os
import datetime
import signal
import sys
import time
import random

from util import *

CONFIG_FILENAME = 'config.txt'
TEST_FILE = 'performancetest.jpg'
# Constant for our buffer size

BUFFER_SIZE = 1024




# this class is for storing server connection information


class ServerConnection:
    def __init__(self, host, port, socket, performance):
        self.host = host
        self.port = port
        self.socket = socket
        self.performance = performance


def prepare_get_message(host, port, file_name):
    request = f'GET {file_name} HTTP/1.1\r\nHost: {host}:{port}\r\n\r\n'
    return request
# Read a file from the socket and print it out.  (For errors primarily.)


def print_file_from_socket(sock, bytes_to_read):

    bytes_read = 0
    while (bytes_read < bytes_to_read):
        chunk = sock.recv(BUFFER_SIZE)
        bytes_read += len(chunk)
        print(chunk.decode())

# Read a file from the socket and save it out.


def save_file_from_socket(sock, bytes_to_read, file_name):

    with open(file_name, 'wb') as file_to_write:
        bytes_read = 0
        while (bytes_read < bytes_to_read):
            chunk = sock.recv(BUFFER_SIZE)
            bytes_read += len(chunk)
            file_to_write.write(chunk)

# Read a single line (ending with \n) from a socket and return it.
# We will strip out the \r and the \n in the process.


def get_line_from_socket(sock):

    done = False
    line = ''
    while (not done):
        char = sock.recv(1).decode()
        if (char == '\r'):
            pass
        elif (char == '\n'):
            done = True
        else:
            line = line + char
    return line

# Create an HTTP response

def prepare_response_message(value):
    date = datetime.datetime.now()
    date_string = 'Date: ' + date.strftime('%a, %d %b %Y %H:%M:%S EDT')
    message = 'HTTP/1.1 '
    if value == '200':
        message = message + value + ' OK\r\n' + date_string + '\r\n'
    elif value == '404':
        message = message + value + ' Not Found\r\n' + date_string + '\r\n'
    elif value == '501':
        message = message + value + ' Method Not Implemented\r\n' + date_string + '\r\n'
    elif value == '505':
        message = message + value + ' Version Not Supported\r\n' + date_string + '\r\n'
    return message


def send_response_to_client(sock, code, file_name, server):

    # Determine content type of file

    type = 'text/html'
    
    # Get size of file

    file_size = os.path.getsize(file_name)

    # Construct header and send it

    url = 'http://' + server.host + ':' + str(server.port) + '/' + file_name
    header = prepare_response_message(code) + 'Content-Type: ' + type + '\r\nContent-Length: ' + str(file_size) + '\r\n' + 'Location: ' + url + '\r\n\r\n'
    sock.send(header.encode())

    # Open the file, read it, and send it

    with open(file_name, 'rb') as file_to_send:
        while True:
            chunk = file_to_send.read(BUFFER_SIZE)
            if chunk:
                sock.send(chunk)
            else:
                break


def receiveFile(sock):
    response_line = get_line_from_socket(sock)
    response_list = response_line.split(' ')
    headers_done = False

    if response_list[1] != '200':
        print('Error:  An error response was received from the server.  Details:\n')
        print(response_line)
        bytes_to_read = 0
        while (not headers_done):
            header_line = get_line_from_socket(sock)
            print(header_line)
            header_list = header_line.split(' ')
            if (header_line == ''):
                headers_done = True
            elif (header_list[0] == 'Content-Length:'):
                bytes_to_read = int(header_list[1])
        print_file_from_socket(sock, bytes_to_read)
        print('The file to test performance cannot be found, therefore the load balancer cannot operate')
                # send back 503 error message to client
        sys.exit(1)


            # If it's OK, we retrieve and write the file out.

    else:

        print('Success:  Server is sending file.  Downloading it now.')

                # If requested file begins with a / we strip it off.


        # Go through headers and find the size of the file, then save it.

        bytes_to_read = 0
        while (not headers_done):
            header_line = get_line_from_socket(sock)
            header_list = header_line.split(' ')
            if (header_line == ''):                            
                headers_done = True
            elif (header_list[0] == 'Content-Length:'):
                bytes_to_read = int(header_list[1])
        save_file_from_socket(sock, bytes_to_read,TEST_FILE)

def testPerformance():
    server_connection_pq = PriorityQueue()
    try:
        config = open(CONFIG_FILENAME, "r+")
    except IOError:
        print("Error: Config File does not appear to exist.")
        sys.exit(1)
    while (1):
        line = config.readline()

        if not line:
            break

        line_split = line.split(':')
        server_host = line_split[0]
        server_port = int(line_split[1])
        print('Connecting to server ...')
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.connect((server_host, server_port))
            server = ServerConnection(server_host, server_port, server_socket, 1000)
            # test the servers for their performance
            # make sure all servers have access to the same file 'performancetest.jpg'
            print('Conducting performance test...')
            test_message = prepare_get_message(server_host,server_port, TEST_FILE)
            start_time = datetime.datetime.now()
            server_socket.send(test_message.encode())
            end_time = datetime.datetime.now()

            server.performance = end_time - start_time
            server_connection_pq.push(server, server.performance)
        except ConnectionRefusedError:
            print('Error:  That host or port is not accepting connections. It will not be added to the list')
            #the server will not be added to the list of servers to evaulate
            


        
    config.close()
    return server_connection_pq


def main() :
    # to read the config and create all the connections with the server
    server_selection_proportional = []
    server_connection_pq = testPerformance()

    
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.bind(('', 0))
    print('Will wait for client connections at port ' +
    str(client_socket.getsockname()[1]))
    client_socket.listen(1)


    # loops forever to allow the load balancer to run
    while(1):

        # this makes it so the servers are selected proportionally to there speed

        print("len of pq" , server_connection_pq.count)
        if server_connection_pq.count > 0:
            for i in range(server_connection_pq.count):
                server = server_connection_pq.pop()
                for j in range(server_connection_pq.count):
                    server_selection_proportional.append(server)


        print('Waiting for incoming client connection ...')
        # sets the timeout to go off after five minutes, after this time a performance test will be done again
        client_socket.settimeout(300)
        
        try: 
            conn, addr = client_socket.accept()
            print(conn)

            
            print('Accepted connection from client address:', addr)
            print('Connection to client established, waiting to receive message...')
        

            # sends the client a 301 with a random server location from the proportional list
            rng = random.randrange(len(server_selection_proportional))
            send_response_to_client(conn, '301', '301.html',server_selection_proportional[rng])
            
            conn.close()
        except socket.timeout: 
            #if the timeout occurs, a performance test will be done
            server_selection_proportional = []
            server_connection_pq = testPerformance()

        server_selection_proportional = []
        server_connection_pq = testPerformance()



if __name__ == '__main__':
    main()