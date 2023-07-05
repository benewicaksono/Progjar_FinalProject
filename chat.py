import base64
import os
from os.path import join, dirname, realpath
import json
import uuid
import logging
from queue import Queue
import threading
import socket
from datetime import datetime


class RealmThreadCommunication(threading.Thread):
    def __init__(self, chats, realm_dest_address, realm_dest_port):
        self.chats = chats
        self.chat = {}
        self.realm_dest_address = realm_dest_address
        self.realm_dest_port = realm_dest_port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.realm_dest_address, self.realm_dest_port))
        threading.Thread.__init__(self)

    def sendstring(self, string):
        try:
            self.sock.sendall(string.encode())
            receivedmsg = ""
            while True:
                data = self.sock.recv(1024)
                print("diterima dari server", data)
                if data:
                    # data harus didecode agar dapat di operasikan dalam bentuk string
                    receivedmsg = "{}{}".format(receivedmsg, data.decode())
                    if receivedmsg[-4:] == "\r\n\r\n":
                        print("end of string")
                        return json.loads(receivedmsg)
        except:
            self.sock.close()
            return {"status": "ERROR", "message": "Gagal"}

    def put(self, message):
        dest = message["msg_to"]
        try:
            self.chat[dest].put(message)
        except KeyError:
            self.chat[dest] = Queue()
            self.chat[dest].put(message)


class Chat:
    def __init__(self):
        self.sessions = {}
        self.users = {}
        self.connectedUsers = {}
        self.realms = {}
        self.load_user_data()  # Load user data from db/user.json file

    # Region ============================= Load User Data =============================
    def load_user_data(self):
        try:
            with open("db/user.json", "r") as file:
                self.users = json.load(file)
        except FileNotFoundError:
            self.users = {}

    # End Region ============================= Load User Data =============================

    # Region ============================= Save User to JSON =============================
    def save_user_data(self):
        with open("db/user.json", "w") as file:
            json.dump(self.users, file, indent=4)

    # End Region ============================= Save User to JSON =============================

    # Region ============================= Register User =============================
    def add_user(self, username, user_data):
        self.users[username] = user_data
        self.save_user_data()

    # End Region ============================= Register User =============================

    # Region ============================= Command List =============================
    def proses(self, data):
        j = data.split(" ")
        try:
            command = j[0].strip()
            if command == "register":
                username = j[1].strip()
                password = j[2].strip()
                name = j[3].strip()
                country = j[4].strip()
                logging.warning(
                    "REGISTER: register {} {} {} {}".format(
                        username, password, name, country
                    )
                )
                return self.register_user(username, password, name, country)

            elif command == "auth":
                username = j[1].strip()
                password = j[2].strip()
                logging.warning("AUTH: auth {} {}".format(username, password))
                return self.user_auth(username, password)

            elif command == "whoami":
                sessionid = j[1].strip()
                logging.warning("WHOAMI: whoami {}".format(sessionid))
                return self.get_whoami(sessionid)

            elif command == "getpresence":
                username = j[1].strip()
                logging.warning("GETPRESENCE: getpresence for user {}".format(username))
                return self.get_presence(username)

            elif command == "send":
                sessionid = j[1].strip()
                usernameto = j[2].strip()
                message = ""
                for w in j[3:]:
                    message = "{} {}".format(message, w)
                usernamefrom = self.sessions[sessionid]["username"]
                logging.warning(
                    "SEND: session {} send message from {} to {}".format(
                        sessionid, usernamefrom, usernameto
                    )
                )
                return self.sendmessage(sessionid, usernamefrom, usernameto, message)

            elif command == "sendgroup":
                sessionid = j[1].strip()
                usernamesto = j[2].strip().split(",")
                message = ""
                for w in j[3:]:
                    message = "{} {}".format(message, w)
                usernamefrom = self.sessions[sessionid]["username"]
                logging.warning(
                    "SEND: session {} send message from {} to {}".format(
                        sessionid, usernamefrom, usernamesto
                    )
                )
                return self.send_group_message(
                    sessionid, usernamefrom, usernamesto, message
                )

            elif command == "inbox":
                sessionid = j[1].strip()
                username = self.sessions[sessionid]["username"]
                logging.warning("INBOX: {}".format(sessionid))
                return self.get_inbox(username)

            elif command == "sendfile":
                sessionid = j[1].strip()
                usernameto = j[2].strip()
                filepath = j[3].strip()
                encoded_file = j[4].strip()
                usernamefrom = self.sessions[sessionid]["username"]
                logging.warning(
                    "SENDFILE: session {} send file from {} to {}".format(
                        sessionid, usernamefrom, usernameto
                    )
                )
                return self.send_file(
                    sessionid, usernamefrom, usernameto, filepath, encoded_file
                )

            elif command == "sendgroupfile":
                sessionid = j[1].strip()
                usernamesto = j[2].strip().split(",")
                filepath = j[3].strip()
                encoded_file = j[4].strip()
                usernamefrom = self.sessions[sessionid]["username"]
                logging.warning(
                    "SENDGROUPFILE: session {} send file from {} to {}".format(
                        sessionid, usernamefrom, usernamesto
                    )
                )
                return self.send_group_file(
                    sessionid, usernamefrom, usernamesto, filepath, encoded_file
                )

            elif command == "addrealm":
                realm_id = j[1].strip()
                realm_dest_address = j[2].strip()
                realm_dest_port = int(j[3].strip())
                return self.add_realm(
                    realm_id, realm_dest_address, realm_dest_port, data
                )

            elif command == "recvrealm":
                realm_id = j[1].strip()
                realm_dest_address = j[2].strip()
                realm_dest_port = int(j[3].strip())
                return self.recv_realm(
                    realm_id, realm_dest_address, realm_dest_port, data
                )

            elif command == "sendprivaterealm":
                sessionid = j[1].strip()
                realm_id = j[2].strip()
                usernameto = j[3].strip()
                message = ""
                for w in j[4:]:
                    message = "{} {}".format(message, w)
                print(message)
                usernamefrom = self.sessions[sessionid]["username"]
                logging.warning(
                    "SENDPRIVATEREALM: session {} send message from {} to {} in realm {}".format(
                        sessionid, usernamefrom, usernameto, realm_id
                    )
                )
                return self.send_realm_message(
                    sessionid, realm_id, usernamefrom, usernameto, message, data
                )

            elif command == "recvrealmprivatemsg":
                usernamefrom = j[1].strip()
                realm_id = j[2].strip()
                usernameto = j[3].strip()
                message = ""
                for w in j[4:]:
                    message = "{} {}".format(message, w)
                print(message)
                logging.warning(
                    "RECVREALMPRIVATEMSG: recieve message from {} to {} in realm {}".format(
                        usernamefrom, usernameto, realm_id
                    )
                )
                return self.recv_realm_message(
                    realm_id, usernamefrom, usernameto, message, data
                )

            elif command == "sendfilerealm":
                sessionid = j[1].strip()
                realm_id = j[2].strip()
                usernameto = j[3].strip()
                filepath = j[4].strip()
                encoded_file = j[5].strip()
                usernamefrom = self.sessions[sessionid]["username"]
                logging.warning(
                    "SENDFILEREALM: session {} send file from {} to {} in realm {}".format(
                        sessionid, usernamefrom, usernameto, realm_id
                    )
                )
                return self.send_file_realm(
                    sessionid,
                    realm_id,
                    usernamefrom,
                    usernameto,
                    filepath,
                    encoded_file,
                    data,
                )

            elif command == "recvfilerealm":
                usernamefrom = j[1].strip()
                realm_id = j[2].strip()
                usernameto = j[3].strip()
                filepath = j[4].strip()
                encoded_file = j[5].strip()
                logging.warning(
                    "RECVFILEREALM: recieve file from {} to {} in realm {}".format(
                        usernamefrom, usernameto, realm_id
                    )
                )
                return self.recv_file_realm(
                    realm_id, usernamefrom, usernameto, filepath, encoded_file, data
                )

            elif command == "sendgrouprealm":
                sessionid = j[1].strip()
                realm_id = j[2].strip()
                usernamesto = j[3].strip().split(",")
                message = ""
                for w in j[4:]:
                    message = "{} {}".format(message, w)
                usernamefrom = self.sessions[sessionid]["username"]
                logging.warning(
                    "SENDGROUPREALM: session {} send message from {} to {} in realm {}".format(
                        sessionid, usernamefrom, usernamesto, realm_id
                    )
                )
                return self.send_group_realm_message(
                    sessionid, realm_id, usernamefrom, usernamesto, message, data
                )

            elif command == "recvrealmgroupmsg":
                usernamefrom = j[1].strip()
                realm_id = j[2].strip()
                usernamesto = j[3].strip().split(",")
                message = ""
                for w in j[4:]:
                    message = "{} {}".format(message, w)
                logging.warning(
                    "RECVGROUPREALM: send message from {} to {} in realm {}".format(
                        usernamefrom, usernamesto, realm_id
                    )
                )
                return self.recv_group_realm_message(
                    realm_id, usernamefrom, usernamesto, message, data
                )

            elif command == "sendgroupfilerealm":
                sessionid = j[1].strip()
                realm_id = j[2].strip()
                usernamesto = j[3].strip().split(",")
                filepath = j[4].strip()
                encoded_file = j[5].strip()
                usernamefrom = self.sessions[sessionid]["username"]
                logging.warning(
                    "SENDGROUPFILEREALM: session {} send file from {} to {} in realm {}".format(
                        sessionid, usernamefrom, usernamesto, realm_id
                    )
                )
                return self.send_group_file_realm(
                    sessionid,
                    realm_id,
                    usernamefrom,
                    usernamesto,
                    filepath,
                    encoded_file,
                    data,
                )

            elif command == "recvgroupfilerealm":
                usernamefrom = j[1].strip()
                realm_id = j[2].strip()
                usernamesto = j[3].strip().split(",")
                filepath = j[4].strip()
                encoded_file = j[5].strip()
                logging.warning(
                    "SENDGROUPFILEREALM: recieve file from {} to {} in realm {}".format(
                        usernamefrom, usernamesto, realm_id
                    )
                )
                return self.recv_group_file_realm(
                    realm_id, usernamefrom, usernamesto, filepath, encoded_file, data
                )

            elif command == "getrealminbox":
                sessionid = j[1].strip()
                realmid = j[2].strip()
                username = self.sessions[sessionid]["username"]
                logging.warning(
                    "GETREALMINBOX: {} from realm {}".format(sessionid, realmid)
                )
                return self.get_realm_inbox(username, realmid)

            elif command == "getrealmchat":
                realmid = j[1].strip()
                username = j[2].strip()
                logging.warning("GETREALMCHAT: from realm {}".format(realmid))
                return self.get_realm_chat(realmid, username)

            else:
                print(command)
                return {"status": "ERROR", "message": "**Protocol Tidak Benar"}
        except KeyError:
            return {"status": "ERROR", "message": "Informasi tidak ditemukan"}
        except IndexError:
            return {"status": "ERROR", "message": "--Protocol Tidak Benar"}

    # Region ============================= Register New User =============================
    def register_user(self, username, password, name, country):
        if username in self.users:
            return {"status": "ERROR", "message": "Username already exists"}

        new_user = {
            "nama": name,
            "negara": country,
            "password": password,
            "incoming": {},
            "outgoing": {},
        }

        # Save new user to user.json file
        try:
            with open("db/user.json", "r+") as file:
                data = json.load(file)
                data[username] = new_user
                file.seek(0)
                json.dump(data, file, indent=4)
                file.truncate()
        except FileNotFoundError:
            return {"status": "ERROR", "message": "user.json file not found"}
        except json.JSONDecodeError:
            return {"status": "ERROR", "message": "user.json file is not valid JSON"}

        self.users[username] = new_user

        return {"status": "OK", "message": "User registered successfully"}

    # EndRegion ========================== Register New User =============================

    # Region ============================= Login =============================
    def user_auth(self, username, password):
        if username not in self.users:
            return {"status": "ERROR", "message": "User not found"}
        if self.users[username]["password"] != password:
            return {"status": "ERROR", "message": "Wrong password"}
        tokenid = str(uuid.uuid4())
        self.sessions[tokenid] = {
            "username": username,
            "userdetail": self.users[username],
        }
        self.connectedUsers[username] = True
        return {"status": "OK", "tokenid": tokenid}

    # EndRegion ========================== Login User =============================

    # Region ============================= WHOAMI =============================
    def get_whoami(self, sessionid):
        if sessionid not in self.sessions:
            return {"status": "ERROR", "message": "Session not found"}
        return {
            "status": "OK",
            "message": "{}".format(self.sessions[sessionid]["username"]),
        }

    # EndRegion ========================== WHOAMI =============================

    # Region ============================= Get Presence Status =============================
    def get_presence(self, username):
        if username in self.users:
            user_data = self.users[username]
            if username in self.connectedUsers:
                presence = "online"
            elif "presence" in user_data:
                presence = user_data["presence"]
            else:
                presence = "offline"
            return {
                "status": "OK",
                "message": "User {} is currently {}".format(username, presence),
            }
        else:
            return {"status": "ERROR", "message": "User not found"}

    # EndRegion ========================== Get Presence Status =============================

    # Region ============================= Get User =============================
    def get_user(self, username):
        if username not in self.users:
            return False
        return self.users[username]

    # EndRegion ========================== Get User =============================

    # Region ============================= Send Private Chat =============================
    def sendmessage(self, sessionid, username_from, username_dest, message):
        if sessionid not in self.sessions:
            return {"status": "ERROR", "message": "Session Tidak Ditemukan"}

        sender = self.get_user(username_from)
        receiver = self.get_user(username_dest)

        if not sender or not receiver:
            return {"status": "ERROR", "message": "User Tidak Ditemukan"}

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        message = {
            "msg_from": sender["nama"],
            "msg_to": receiver["nama"],
            "msg": message,
            "timestamp": timestamp,
        }

        outqueue_sender = sender.setdefault("outgoing", {})
        inqueue_receiver = receiver.setdefault("incoming", {})

        outqueue_sender.setdefault(username_from, Queue()).put(message)
        inqueue_receiver.setdefault(username_from, Queue()).put(message)

        return {"status": "OK", "message": "Message Sent"}

    # EndRegion ========================== Send Private Chat =============================

    def send_group_message(self, sessionid, username_from, usernames_dest, message):
        if sessionid not in self.sessions:
            return {"status": "ERROR", "message": "Session not found"}
        s_fr = self.get_user(username_from)
        if s_fr is False:
            return {"status": "ERROR", "message": "User not found"}
        for username_dest in usernames_dest:
            s_to = self.get_user(username_dest)
            if s_to is False:
                continue
            message = {"msg_from": s_fr["nama"], "msg_to": s_to["nama"], "msg": message}
            outqueue_sender = s_fr["outgoing"]
            inqueue_receiver = s_to["incoming"]
            try:
                outqueue_sender[username_from].put(message)
            except KeyError:
                outqueue_sender[username_from] = Queue()
                outqueue_sender[username_from].put(message)
            try:
                inqueue_receiver[username_from].put(message)
            except KeyError:
                inqueue_receiver[username_from] = Queue()
                inqueue_receiver[username_from].put(message)
        return {"status": "OK", "message": "Message Sent"}

    # Region ============================= Get Inbox =============================
    def get_inbox(self, username):
        user = self.get_user(username)

        if not user:
            return {"status": "ERROR", "message": "User Tidak Ditemukan"}

        incoming = user.setdefault("incoming", {})
        msgs = {}

        for user in incoming:
            msgs[user] = []
            while not incoming[user].empty():
                message = incoming[user].get()
                msgs[user].append(message)

                message["read"] = True

        return {"status": "OK", "messages": msgs}

    # EndRegion ========================== Get Inbox =============================

    def send_file(
        self, sessionid, username_from, username_dest, filepath, encoded_file
    ):
        if sessionid not in self.sessions:
            return {"status": "ERROR", "message": "Session not found"}

        s_fr = self.get_user(username_from)
        s_to = self.get_user(username_dest)

        if s_fr is False or s_to is False:
            return {"status": "ERROR", "message": "User not found"}

        filename = os.path.basename(filepath)
        message = {
            "msg_from": s_fr["nama"],
            "msg_to": s_to["nama"],
            "file_name": filename,
            "file_content": encoded_file,
        }

        outqueue_sender = s_fr["outgoing"]
        inqueue_receiver = s_to["incoming"]
        try:
            outqueue_sender[username_from].put(json.dumps(message))
        except KeyError:
            outqueue_sender[username_from] = Queue()
            outqueue_sender[username_from].put(json.dumps(message))
        try:
            inqueue_receiver[username_from].put(json.dumps(message))
        except KeyError:
            inqueue_receiver[username_from] = Queue()
            inqueue_receiver[username_from].put(json.dumps(message))

        now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        folder_name = f"{now}_{username_from}_{username_dest}_{filename}"
        folder_path = join(dirname(realpath(__file__)), "files/")
        os.makedirs(folder_path, exist_ok=True)
        folder_path = join(folder_path, folder_name)
        os.makedirs(folder_path, exist_ok=True)
        file_destination = os.path.join(folder_path, filename)
        if "b" in encoded_file[0]:
            msg = encoded_file[2:-1]

            with open(file_destination, "wb") as fh:
                fh.write(base64.b64decode(msg))
        else:
            tail = encoded_file.split()

        self.sendmessage(sessionid, username_from, username_dest, msg)
        return {"status": "OK", "message": "File Sent"}

    def send_group_file(
        self, sessionid, username_from, usernames_dest, filepath, encoded_file
    ):
        if sessionid not in self.sessions:
            return {"status": "ERROR", "message": "Session Tidak Ditemukan"}
        s_fr = self.get_user(username_from)
        if s_fr is False:
            return {"status": "ERROR", "message": "User Tidak Ditemukan"}

        filename = os.path.basename(filepath)
        for username_dest in usernames_dest:
            s_to = self.get_user(username_dest)
            if s_to is False:
                continue
            message = {
                "msg_from": s_fr["nama"],
                "msg_to": s_to["nama"],
                "file_name": filename,
                "file_content": encoded_file,
            }

            outqueue_sender = s_fr["outgoing"]
            inqueue_receiver = s_to["incoming"]
            try:
                outqueue_sender[username_from].put(json.dumps(message))
            except KeyError:
                outqueue_sender[username_from] = Queue()
                outqueue_sender[username_from].put(json.dumps(message))
            try:
                inqueue_receiver[username_from].put(json.dumps(message))
            except KeyError:
                inqueue_receiver[username_from] = Queue()
                inqueue_receiver[username_from].put(json.dumps(message))

            now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            folder_name = f"{now}_{username_from}_{username_dest}_{filename}"
            folder_path = join(dirname(realpath(__file__)), "files/")
            os.makedirs(folder_path, exist_ok=True)
            folder_path = join(folder_path, folder_name)
            os.makedirs(folder_path, exist_ok=True)
            file_destination = os.path.join(folder_path, filename)
            if "b" in encoded_file[0]:
                msg = encoded_file[2:-1]
                with open(file_destination, "wb") as fh:
                    fh.write(base64.b64decode(msg))
            else:
                tail = encoded_file.split()

        return {"status": "OK", "message": "File Sent"}

    def add_realm(self, realm_id, realm_dest_address, realm_dest_port, data):
        j = data.split()
        print(j[0], realm_id, realm_dest_address, realm_dest_port, data)
        j[0] = "recvrealm"
        data = " ".join(j)
        data += "\r\n"
        print(data)
        if realm_id in self.realms:
            return {"status": "ERROR", "message": "Realm sudah ada"}

        print("sebelum RealmThreadComm")
        self.realms[realm_id] = RealmThreadCommunication(
            self, realm_dest_address, realm_dest_port
        )
        print("sesudah RealmThreadComm")
        result = self.realms[realm_id].sendstring(data)
        return result

    def recv_realm(self, realm_id, realm_dest_address, realm_dest_port, data):
        self.realms[realm_id] = RealmThreadCommunication(
            self, realm_dest_address, realm_dest_port
        )
        return {"status": "OK"}

    def send_realm_message(
        self, sessionid, realm_id, username_from, username_dest, message, data
    ):
        if sessionid not in self.sessions:
            return {"status": "ERROR", "message": "Session Tidak Ditemukan"}
        if realm_id not in self.realms:
            return {"status": "ERROR", "message": "Realm Tidak Ditemukan"}
        s_fr = self.get_user(username_from)
        s_to = self.get_user(username_dest)
        if s_fr == False or s_to == False:
            return {"status": "ERROR", "message": "User Tidak Ditemukan"}
        message = {"msg_from": s_fr["nama"], "msg_to": s_to["nama"], "msg": message}
        self.realms[realm_id].put(message)

        j = data.split()
        j[0] = "recvrealmprivatemsg"
        j[1] = username_from
        data = " ".join(j)
        data += "\r\n"
        self.realms[realm_id].sendstring(data)
        return {"status": "OK", "message": "Message Sent to Realm"}

    def recv_realm_message(self, realm_id, username_from, username_dest, message, data):
        if realm_id not in self.realms:
            return {"status": "ERROR", "message": "Realm Tidak Ditemukan"}
        s_fr = self.get_user(username_from)
        s_to = self.get_user(username_dest)
        if s_fr == False or s_to == False:
            return {"status": "ERROR", "message": "User Tidak Ditemukan"}
        message = {"msg_from": s_fr["nama"], "msg_to": s_to["nama"], "msg": message}
        self.realms[realm_id].put(message)
        return {"status": "OK", "message": "Message Sent to Realm"}

    def send_file_realm(
        self,
        sessionid,
        realm_id,
        username_from,
        username_dest,
        filepath,
        encoded_file,
        data,
    ):
        if sessionid not in self.sessions:
            return {"status": "ERROR", "message": "Session Tidak Ditemukan"}
        if realm_id not in self.realms:
            return {"status": "ERROR", "message": "Realm Tidak Ditemukan"}
        s_fr = self.get_user(username_from)
        s_to = self.get_user(username_dest)
        if s_fr == False or s_to == False:
            return {"status": "ERROR", "message": "User Tidak Ditemukan"}

        filename = os.path.basename(filepath)
        message = {
            "msg_from": s_fr["nama"],
            "msg_to": s_to["nama"],
            "file_name": filename,
            "file_content": encoded_file,
        }
        self.realms[realm_id].put(message)

        now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        folder_name = f"{now}_{username_from}_{username_dest}_{filename}"
        folder_path = join(dirname(realpath(__file__)), "files/")
        os.makedirs(folder_path, exist_ok=True)
        folder_path = join(folder_path, folder_name)
        os.makedirs(folder_path, exist_ok=True)
        file_destination = os.path.join(folder_path, filename)
        if "b" in encoded_file[0]:
            msg = encoded_file[2:-1]

            with open(file_destination, "wb") as fh:
                fh.write(base64.b64decode(msg))
        else:
            tail = encoded_file.split()
        print(file_destination)
        j = data.split()
        j[0] = "recvfilerealm"
        j[1] = username_from
        data = " ".join(j)
        data += "\r\n"
        self.realms[realm_id].sendstring(data)
        return {"status": "OK", "message": "File Sent to Realm"}

    def recv_file_realm(
        self, realm_id, username_from, username_dest, filepath, encoded_file, data
    ):
        if realm_id not in self.realms:
            return {"status": "ERROR", "message": "Realm Tidak Ditemukan"}
        s_fr = self.get_user(username_from)
        s_to = self.get_user(username_dest)
        if s_fr == False or s_to == False:
            return {"status": "ERROR", "message": "User Tidak Ditemukan"}

        filename = os.path.basename(filepath)
        message = {
            "msg_from": s_fr["nama"],
            "msg_to": s_to["nama"],
            "file_name": filename,
            "file_content": encoded_file,
        }
        self.realms[realm_id].put(message)

        now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        folder_name = f"{now}_{username_from}_{username_dest}_{filename}"
        folder_path = join(dirname(realpath(__file__)), "files/")
        os.makedirs(folder_path, exist_ok=True)
        folder_path = join(folder_path, folder_name)
        os.makedirs(folder_path, exist_ok=True)
        file_destination = os.path.join(folder_path, filename)
        if "b" in encoded_file[0]:
            msg = encoded_file[2:-1]

            with open(file_destination, "wb") as fh:
                fh.write(base64.b64decode(msg))
        else:
            tail = encoded_file.split()

        return {"status": "OK", "message": "File Received to Realm"}

    def send_group_realm_message(
        self, sessionid, realm_id, username_from, usernames_to, message, data
    ):
        if sessionid not in self.sessions:
            return {"status": "ERROR", "message": "Session Tidak Ditemukan"}
        if realm_id not in self.realms:
            return {"status": "ERROR", "message": "Realm Tidak Ditemukan"}
        s_fr = self.get_user(username_from)
        for username_to in usernames_to:
            s_to = self.get_user(username_to)
            message = {"msg_from": s_fr["nama"], "msg_to": s_to["nama"], "msg": message}
            self.realms[realm_id].put(message)

        j = data.split()
        j[0] = "recvrealmgroupmsg"
        j[1] = username_from
        data = " ".join(j)
        data += "\r\n"
        self.realms[realm_id].sendstring(data)
        return {"status": "OK", "message": "Message Sent to Group in Realm"}

    def recv_group_realm_message(
        self, realm_id, username_from, usernames_to, message, data
    ):
        if realm_id not in self.realms:
            return {"status": "ERROR", "message": "Realm Tidak Ditemukan"}
        s_fr = self.get_user(username_from)
        for username_to in usernames_to:
            s_to = self.get_user(username_to)
            message = {"msg_from": s_fr["nama"], "msg_to": s_to["nama"], "msg": message}
            self.realms[realm_id].put(message)
        return {"status": "OK", "message": "Message Sent to Group in Realm"}

    def send_group_file_realm(
        self,
        sessionid,
        realm_id,
        username_from,
        usernames_to,
        filepath,
        encoded_file,
        data,
    ):
        if sessionid not in self.sessions:
            return {"status": "ERROR", "message": "Session Tidak Ditemukan"}
        if realm_id not in self.realms:
            return {"status": "ERROR", "message": "Realm Tidak Ditemukan"}
        s_fr = self.get_user(username_from)

        if s_fr == False:
            return {"status": "ERROR", "message": "User Tidak Ditemukan"}

        filename = os.path.basename(filepath)
        for username_to in usernames_to:
            s_to = self.get_user(username_to)
            message = {
                "msg_from": s_fr["nama"],
                "msg_to": s_to["nama"],
                "file_name": filename,
                "file_content": encoded_file,
            }
            self.realms[realm_id].put(message)

            now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            folder_name = f"{now}_{username_from}_{username_to}_{filename}"
            folder_path = join(dirname(realpath(__file__)), "files/")
            os.makedirs(folder_path, exist_ok=True)
            folder_path = join(folder_path, folder_name)
            os.makedirs(folder_path, exist_ok=True)
            file_destination = os.path.join(folder_path, filename)
            if "b" in encoded_file[0]:
                msg = encoded_file[2:-1]

                with open(file_destination, "wb") as fh:
                    fh.write(base64.b64decode(msg))
            else:
                tail = encoded_file.split()

        j = data.split()
        j[0] = "recvgroupfilerealm"
        j[1] = username_from
        data = " ".join(j)
        data += "\r\n"
        self.realms[realm_id].sendstring(data)
        return {"status": "OK", "message": "Message Sent to Group in Realm"}

    def recv_group_file_realm(
        self, realm_id, username_from, usernames_to, filepath, encoded_file, data
    ):
        if realm_id not in self.realms:
            return {"status": "ERROR", "message": "Realm Tidak Ditemukan"}
        s_fr = self.get_user(username_from)

        if s_fr == False:
            return {"status": "ERROR", "message": "User Tidak Ditemukan"}

        filename = os.path.basename(filepath)
        for username_to in usernames_to:
            s_to = self.get_user(username_to)
            message = {
                "msg_from": s_fr["nama"],
                "msg_to": s_to["nama"],
                "file_name": filename,
                "file_content": encoded_file,
            }
            self.realms[realm_id].put(message)

            now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            folder_name = f"{now}_{username_from}_{username_to}_{filename}"
            folder_path = join(dirname(realpath(__file__)), "files/")
            os.makedirs(folder_path, exist_ok=True)
            folder_path = join(folder_path, folder_name)
            os.makedirs(folder_path, exist_ok=True)
            file_destination = os.path.join(folder_path, filename)
            if "b" in encoded_file[0]:
                msg = encoded_file[2:-1]

                with open(file_destination, "wb") as fh:
                    fh.write(base64.b64decode(msg))
            else:
                tail = encoded_file.split()

        return {"status": "OK", "message": "Message Sent to Group in Realm"}

    def get_realm_inbox(self, username, realmid):
        if realmid not in self.realms:
            return {"status": "ERROR", "message": "Realm Tidak Ditemukan"}
        # s_fr = self.get_user(username)
        result = self.realms[realmid].sendstring(
            "getrealmchat {} {}\r\n".format(realmid, username)
        )
        return result

    def get_realm_chat(self, realmid, username):
        s_fr = self.get_user(username)
        msgs = []
        while not self.realms[realmid].chat[s_fr["nama"]].empty():
            msgs.append(self.realms[realmid].chat[s_fr["nama"]].get_nowait())
        return {"status": "OK", "messages": msgs}


if __name__ == "__main__":
    j = Chat()
    while True:
        print("\n")
        cmdline = input("Command {}:".format(j.proses))
        print(j.proses(cmdline))
    sesi = j.proses("auth messi surabaya")
    print(sesi)
