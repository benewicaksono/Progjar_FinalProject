import socket
import json
import base64
import json
import os

TARGET_IP = "localhost"
TARGET_PORT = 9999


class ChatClient:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_address = (TARGET_IP, TARGET_PORT)
        self.sock.connect(self.server_address)
        self.tokenid = ""

    def proses(self, cmdline):
        j = cmdline.split(" ")
        try:
            command = j[0].strip()
            if command == "register":
                username = j[1].strip()
                password = j[2].strip()
                name = j[3].strip()
                country = j[4].strip()
                return self.register_user(username, password, name, country)

            elif command == "auth":
                username = j[1].strip()
                password = j[2].strip()
                return self.login(username, password)

            elif command == "whoami":
                return self.whoami()

            elif command == "getpresence":
                username = j[1].strip()
                return self.get_presence(username)

            elif command == "addrealm":
                realmid = j[1].strip()
                realm_address = j[2].strip()
                realm_port = j[3].strip()
                return self.add_realm(realmid, realm_address, realm_port)

            elif command == "send":
                usernameto = j[1].strip()
                message = ""
                for w in j[2:]:
                    message = "{} {}".format(message, w)
                return self.sendmessage(usernameto, message)

            elif command == "sendfile":
                usernameto = j[1].strip()
                filepath = j[2].strip()
                return self.send_file(usernameto, filepath)

            elif command == "sendgroup":
                usernamesto = j[1].strip()
                message = ""
                for w in j[2:]:
                    message = "{} {}".format(message, w)
                return self.send_group_message(usernamesto, message)

            elif command == "sendgroupfile":
                usernamesto = j[1].strip()
                filepath = j[2].strip()
                return self.send_group_file(usernamesto, filepath)

            elif command == "sendprivaterealm":
                realmid = j[1].strip()
                username_to = j[2].strip()
                message = ""
                for w in j[3:]:
                    message = "{} {}".format(message, w)
                return self.send_realm_message(realmid, username_to, message)

            elif command == "sendfilerealm":
                realmid = j[1].strip()
                usernameto = j[2].strip()
                filepath = j[3].strip()
                return self.send_file_realm(realmid, usernameto, filepath)

            elif command == "sendgrouprealm":
                realmid = j[1].strip()
                usernamesto = j[2].strip()
                message = ""
                for w in j[3:]:
                    message = "{} {}".format(message, w)
                return self.send_group_realm_message(realmid, usernamesto, message)

            elif command == "sendgroupfilerealm":
                realmid = j[1].strip()
                usernamesto = j[2].strip()
                filepath = j[3].strip()
                return self.send_group_file_realm(realmid, usernamesto, filepath)

            elif command == "inbox":
                return self.inbox()

            elif command == "getrealminbox":
                realmid = j[1].strip()
                return self.realm_inbox(realmid)

            else:
                return "*Maaf, command tidak benar"
        except IndexError:
            return "-Maaf, command tidak benar"

    def sendstring(self, string):
        try:
            self.sock.sendall(string.encode())
            receivemsg = ""
            while True:
                data = self.sock.recv(1024)
                print("diterima dari server", data)
                if data:
                    receivemsg = "{}{}".format(receivemsg, data.decode())
                    if receivemsg[-4:] == "\r\n\r\n":
                        print("end of string")
                        return json.loads(receivemsg)
        except:
            self.sock.close()
            return {"status": "ERROR", "message": "Gagal"}

    def register_user(self, username, password, name, country):
        if self.tokenid != "":
            return "Error, already logged in"

        string = "register {} {} {} {} \r\n".format(username, password, name, country)
        result = self.sendstring(string)
        if result["status"] == "OK":
            return "User registered successfully"
        else:
            return "Error, {}".format(result["message"])

    def login(self, username, password):
        string = "auth {} {} \r\n".format(username, password)
        result = self.sendstring(string)
        if result["status"] == "OK":
            self.tokenid = result["tokenid"]
            return "username {} logged in, token {} ".format(username, self.tokenid)
        else:
            return "Error, {}".format(result["message"])

    def whoami(self):
        if self.tokenid == "":
            return "Error, not authorized"
        string = "whoami {} \r\n".format(self.tokenid)
        result = self.sendstring(string)
        if result["status"] == "OK":
            return "You are {}".format(result["message"])
        else:
            return "Error, {}".format(result["message"])

    def get_presence(self, username):
        string = "getpresence {}\r\n".format(username)
        result = self.sendstring(string)
        if result["status"] == "OK":
            return result["message"]
        else:
            return "Error, {}".format(result["message"])

    def add_realm(self, realmid, realm_address, realm_port):
        if self.tokenid == "":
            return "Error, not authorized"
        string = "addrealm {} {} {} \r\n".format(realmid, realm_address, realm_port)
        result = self.sendstring(string)
        if result["status"] == "OK":
            return "Realm {} added".format(realmid)
        else:
            return "Error, {}".format(result["message"])

    def sendmessage(self, usernameto="xxx", message="xxx"):
        if self.tokenid == "":
            return "Error, not authorized"

        # Replacing emoticons
        emoticon_mapping = {
            ":)": "🙂",
            ":(": "☹️",
            ":D": "😁",
            "T_T": "😭",
        }
        for emoticon, replacement in emoticon_mapping.items():
            if emoticon in message:
                message = message.replace(emoticon, replacement)

        string = "send {} {} {} \r\n".format(self.tokenid, usernameto, message)
        result = self.sendstring(string)

        if result["status"] == "OK":
            return "Message sent to {}".format(usernameto)
        else:
            return "Error: {}".format(result["message"])

    def send_file(self, usernameto="xxx", filepath="xxx"):
        if self.tokenid == "":
            return "Error, not authorized"

        if not os.path.exists(filepath):
            return {"status": "ERROR", "message": "File not found"}

        with open(filepath, "rb") as file:
            file_content = file.read()
            encoded_content = base64.b64encode(file_content)
        string = "sendfile {} {} {} {}\r\n".format(
            self.tokenid, usernameto, filepath, encoded_content
        )

        result = self.sendstring(string)
        if result["status"] == "OK":
            return "file sent to {}".format(usernameto)
        else:
            return "Error, {}".format(result["message"])

    def send_realm_message(self, realmid, username_to, message):
        if self.tokenid == "":
            return "Error, not authorized"

        # Replacing emoticons
        emoticon_mapping = {
            ":)": "🙂",
            ":(": "☹️",
            ":D": "😁",
            "T_T": "😭",
        }
        for emoticon, replacement in emoticon_mapping.items():
            if emoticon in message:
                message = message.replace(emoticon, replacement)
        string = "sendprivaterealm {} {} {} {}\r\n".format(
            self.tokenid, realmid, username_to, message
        )
        result = self.sendstring(string)
        if result["status"] == "OK":
            return "Message sent to realm {}".format(realmid)
        else:
            return "Error, {}".format(result["message"])

    def send_file_realm(self, realmid, usernameto, filepath):
        if self.tokenid == "":
            return "Error, not authorized"
        if not os.path.exists(filepath):
            return {"status": "ERROR", "message": "File not found"}

        with open(filepath, "rb") as file:
            file_content = file.read()
            encoded_content = base64.b64encode(file_content)
        string = "sendfilerealm {} {} {} {} {}\r\n".format(
            self.tokenid, realmid, usernameto, filepath, encoded_content
        )
        result = self.sendstring(string)
        if result["status"] == "OK":
            return "File sent to realm {}".format(realmid)
        else:
            return "Error, {}".format(result["message"])

    def send_group_message(self, usernames_to="xxx", message="xxx"):
        if self.tokenid == "":
            return "Error, not authorized"

        # Replacing emoticons
        emoticon_mapping = {
            ":)": "🙂",
            ":(": "☹️",
            ":D": "😁",
            "T_T": "😭",
        }
        for emoticon, replacement in emoticon_mapping.items():
            if emoticon in message:
                message = message.replace(emoticon, replacement)
        string = "sendgroup {} {} {} \r\n".format(self.tokenid, usernames_to, message)
        print(string)
        result = self.sendstring(string)
        if result["status"] == "OK":
            return "message sent to {}".format(usernames_to)
        else:
            return "Error, {}".format(result["message"])

    def send_group_file(self, usernames_to="xxx", filepath="xxx"):
        if self.tokenid == "":
            return "Error, not authorized"

        if not os.path.exists(filepath):
            return {"status": "ERROR", "message": "File not found"}

        with open(filepath, "rb") as file:
            file_content = file.read()
            encoded_content = base64.b64encode(file_content)

        string = "sendgroupfile {} {} {} {}\r\n".format(
            self.tokenid, usernames_to, filepath, encoded_content
        )

        result = self.sendstring(string)
        if result["status"] == "OK":
            return "file sent to {}".format(usernames_to)
        else:
            return "Error, {}".format(result["message"])

    def send_group_realm_message(self, realmid, usernames_to, message):
        if self.tokenid == "":
            return "Error, not authorized"

        # Replacing emoticons
        emoticon_mapping = {
            ":)": "🙂",
            ":(": "☹️",
            ":D": "😁",
            "T_T": "😭",
        }
        for emoticon, replacement in emoticon_mapping.items():
            if emoticon in message:
                message = message.replace(emoticon, replacement)
        string = "sendgrouprealm {} {} {} {} \r\n".format(
            self.tokenid, realmid, usernames_to, message
        )

        result = self.sendstring(string)
        if result["status"] == "OK":
            return "message sent to group {} in realm {}".format(usernames_to, realmid)
        else:
            return "Error {}".format(result["message"])

    def send_group_file_realm(self, realmid, usernames_to, filepath):
        if self.tokenid == "":
            return "Error, not authorized"

        if not os.path.exists(filepath):
            return {"status": "ERROR", "message": "File not found"}

        with open(filepath, "rb") as file:
            file_content = file.read()
            encoded_content = base64.b64encode(file_content)
        string = "sendgroupfilerealm {} {} {} {} {}\r\n".format(
            self.tokenid, realmid, usernames_to, filepath, encoded_content
        )

        result = self.sendstring(string)
        if result["status"] == "OK":
            return "file sent to group {} in realm {}".format(usernames_to, realmid)
        else:
            return "Error {}".format(result["message"])

    def inbox(self):
        if self.tokenid == "":
            return "Error, not authorized"

        string = "inbox {} \r\n".format(self.tokenid)
        result = self.sendstring(string)

        if result["status"] == "OK":
            messages = result["messages"]
            emoji_mapping = {
                "\ud83d\ude42": "🙂",
                "\ud83d\ude01": "😁",
                "\u2639\ufe0f": "☹️",
                "\ud83d\ude2d": "😭",
            }

            for username, user_messages in messages.items():
                for msg in user_messages:
                    for emoji, replacement in emoji_mapping.items():
                        msg["msg"] = msg["msg"].replace(emoji, replacement)

            formatted_messages = "\n".join(
                str(msg) for user_messages in messages.values() for msg in user_messages
            )
            return formatted_messages
        else:
            return "Error, {}".format(result["message"])

    def realm_inbox(self, realmid):
        if self.tokenid == "":
            return "Error, not authorized"

        string = "getrealminbox {} {} \r\n".format(self.tokenid, realmid)
        result = self.sendstring(string)

        if result["status"] == "OK":
            messages = result["messages"]
            emoji_mapping = {
                "\ud83d\ude42": "🙂",
                "\ud83d\ude01": "😁",
                "\u2639\ufe0f": "☹️",
                "\ud83d\ude2d": "😭",
            }

            formatted_messages = ""
            for msg in messages:
                if "msg" in msg:
                    for emoji, replacement in emoji_mapping.items():
                        msg["msg"] = msg["msg"].replace(emoji, replacement)
                    formatted_messages += "Message: {}\n".format(msg["msg"])

                if "file_name" in msg and "file_content" in msg:
                    file_name = msg["file_name"]
                    file_content = msg["file_content"]
                    file_data = base64.b64decode(file_content).decode()
                    formatted_messages += "File: {}\n{}\n".format(file_name, file_data)

            return "Message received from realm {}: \n{}".format(
                realmid, formatted_messages
            )
        else:
            return "Error, {}".format(result["message"])


if __name__ == "__main__":
    cc = ChatClient()
    while True:
        print("\n")
        cmdline = input("Command {}:".format(cc.tokenid))
        print(cc.proses(cmdline))
