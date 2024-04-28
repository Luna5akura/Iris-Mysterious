# coding=utf-8
from burp import IBurpExtender, IProxyListener, IHttpListener
from java.io import PrintWriter
from java.net import URL, HttpURLConnection
import sys
import re

if sys.version_info[0] == 2:  # Jython 默认使用的是 Python 2
    reload(sys)
    sys.setdefaultencoding("utf-8")


class BurpExtender(IBurpExtender, IHttpListener, IProxyListener):

    def registerExtenderCallbacks(self, callbacks):
        self._callbacks = callbacks
        self._helpers = callbacks.getHelpers()
        self._stdout = PrintWriter(callbacks.getStdout(), True)
        self._stderr = PrintWriter(callbacks.getStderr(), True)

        self.regex_pattern = re.compile(r'rkyfxfex')  # Define your regex pattern here
        callbacks.setExtensionName("HTTP Traffic Sender")
        # callbacks.registerHttpListener(self)
        callbacks.registerProxyListener(self)
        self._stdout.println("Plugin loaded successfully.")

    def processProxyMessage(self, messageIsRequest, message):
        # 获取请求或响应数据
        self._stdout.println("catch message!")
        messageInfo = message.getMessageInfo()
        messageID = message.getMessageReference()
        data = messageInfo.getRequest() if messageIsRequest else messageInfo.getResponse()
        try:
            if self.regex_pattern.findall(data):
                self.sendData(self._helpers.bytesToString(data), str(messageID))
            else:
                self._stdout.println("Data didn't send: " + str(data.decode('utf-8'))[:100])

        except Exception as e:
            self._stderr.println("Error sending data: " + str(e))

    def sendData(self, data, messageID):
        import json
        try:
            url = URL("http://localhost:1346/receive")
            conn = url.openConnection()
            conn.setDoOutput(True)
            conn.setRequestMethod("POST")
            conn.setRequestProperty("Content-Type", "application/json")
            out = conn.getOutputStream()
            # Package data and messageID into JSON
            payload = json.dumps({"data": data, "messageID": messageID})
            out.write(payload.encode('utf-8'))
            out.close()

            responseCode = conn.getResponseCode()
            self._stdout.println("Data sent with response code: " + str(responseCode))
        except Exception as e:
            self._stderr.println("Error sending data: " + str(e))
