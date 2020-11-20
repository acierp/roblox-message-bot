import httpx
import asyncio
import os
from os import system
import sys
import itertools
import time
import traceback
import json

import os
import time
import requests
import subprocess
import tkinter
from tkinter import messagebox
import sys
import hashlib

with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)
speed = config['threads']


class InvalidCookie(Exception):

    def __init__(self, error, cookie):
        print(f"{error}\n Found Invalid Cookie: {cookie}")


class InvalidToken(Exception):

    def __init__(self, error, token, cookie):
        print(f"{error}\n Found Invalid Token: {token}\n Cookie: {cookie}")


class BadProxy(Exception):

    def __init__(self, error, proxy):
        print(f"{error}\n Found Bad Proxy: {proxy}")


class UnknownError(Exception):

    def __init__(self, error, location):
        print(f"Uncountered Unknown Error in {location}: {error}")


def loadMessage():
    while True:
        try:
            messagePath = os.path.join(os.path.dirname(
                os.path.abspath(__file__)), "message.txt")
            with open(messagePath, "r") as messageFile:
                return messageFile.read()
        except Exception as error:
            if isinstance(error, FileNotFoundError):
                input("message.txt not found. Press Enter to try again.")
                continue
            else:
                raise UnknownError(error, "loadMessage")


async def loadCookies(loop):
    cookieQueue = asyncio.Queue(loop=loop)
    cookiesPath = os.path.join(os.path.dirname(
        os.path.abspath(__file__)), "cookies.txt")
    while True:
        try:
            with open(cookiesPath, "r") as cookiesFile:
                for line in cookiesFile.readlines():
                    await cookieQueue.put(line.split("_")[-1].strip())
            break
        except Exception as error:
            if isinstance(error, FileNotFoundError):
                input("cookies.txt not found. Press Enter to try again.")
                continue
            else:
                raise UnknownError(error, "loadCookies")
    await cookieQueue.put(None)
    return cookieQueue


def loadProxies():
    proxies = []
    proxiesPath = os.path.join(os.path.dirname(
        os.path.abspath(__file__)), "proxies.txt")
    while True:
        try:
            with open(proxiesPath, "r") as proxiesFile:
                for line in proxiesFile.readlines():
                    proxies.append(line.strip())
        except Exception as error:
            if isinstance(error, FileNotFoundError):
                input("proxies.txt not found. Press Enter to try again.")
                continue
            else:
                raise UnknownError(error, "loadProxies")
        return proxies


async def getCSRFToken(securityCookie, proxy):
    while True:
        try:
            async with httpx.AsyncClient(proxies=proxy) as client:
                request = await client.post("https://auth.roblox.com/v1/logout", headers={"Cookie": securityCookie})
        except Exception as error:
            raise BadProxy(error, proxy)

        try:
            return request.headers["x-csrf-token"]
        except:
            if request.status_code == 429:
                continue
            elif request.status_code == 401:
                raise InvalidCookie(
                    "An invalid cookie was passed into getCSRFToken", securityCookie)
            else:
                print(
                    f"Encountered unknown error in getCSRFToken: {request.status_code} {f'Status Code: {request.status_code}' if request.status_code != None else ''}")


async def grabID(securityCookie, proxy):
    # https://www.roblox.com/game/GetCurrentUser.ashx
    while True:
        try:
            async with httpx.AsyncClient(proxies=proxy) as client:
                request = await client.get("http://www.roblox.com/game/GetCurrentUser.ashx", headers={"Cookie": securityCookie}, timeout=15)
        except Exception as error:
            print("First error")
            print(repr(error))
            traceback.print_exc()
            print(error)
            print(request)
            print(request.text)
            print(request.status_code)
            raise UnknownError(error, "grabID")
        if request.status_code == 403 or request.text == "null":
            print("Invalid Cookie test")
            raise InvalidCookie("Invalid Cookie in grabID", securityCookie)
        elif request.status_code == 429:
            print("429 test")
            continue
        else:
            return request.text


# async def grabFriends(id, securityCookie, csrfToken):
    # friendsList = []
    # while True:
        # try:
            # async with httpx.AsyncClient() as client:
            # request = await client.get(f"https://friends.roblox.com/v1/users/{id}/friends", headers={"Cookie": securityCookie, "X-CSRF-TOKEN": csrfToken})
        # except Exception as error:
            # raise UnknownError(error, "grabFriends")

        # try:
            # for user in request.json()["data"]:
            # friendsList.append(user["id"])
        # except Exception as error:
            # if request.status_code == 429:
            # continue
            # raise UnknownError(error, "grabFriends")

        # return friendsList

async def gatherData(mainQueue, cookieQueue):
    while True:
        cookie = await cookieQueue.get()
        if cookie == None:
            await mainQueue.put(None)
            return

        cookie = ".ROBLOSECURITY=_|WARNING:-DO-NOT-SHARE-THIS.--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-steal-your-ROBUX-and-items.|_" + cookie

        userDataDict = {}
        userDataDict["cookie"] = cookie

        global proxyList
        proxy = proxyList[0]
        del proxyList[0]
        proxyList.append(proxy)
        proxy = {"all://": f"http://{proxy}"}
        userDataDict["proxy"] = proxy
        print(proxy)

        try:
            id = await grabID(cookie, proxy)
        except:
            print("Continued grabID")
            continue
        userDataDict["id"] = id

        try:
            token = await getCSRFToken(cookie, proxy)
        except:
            print("continued csrf")
            continue

        userDataDict["token"] = token

        try:
            conversationsList = await grabConversations(cookie, token, proxy)
        except:
            print("Continued conversations")
            continue
        if conversationsList == []:
            continue
        userDataDict["conversations"] = conversationsList

        print(f"Added {userDataDict['id']}")
        await mainQueue.put(userDataDict)


async def grabConversations(securityCookie, csrfToken, proxy):
    conversations = []
    page = 1
    while True:
        try:
            async with httpx.AsyncClient(proxies=proxy) as client:
                request = await client.get(f"https://chat.roblox.com/v2/get-user-conversations?pageNumber={page}&pageSize=1000", headers={"Cookie": securityCookie, "X-CSRF-TOKEN": csrfToken})
        except Exception as error:
            raise UnknownError(error, "grabConversations")

        try:
            for conversation in request.json():
                conversations.append(conversation["id"])
            page += 1
        except Exception as error:
            if request.status_code == 429:
                continue
            elif request.status_code == 401:
                raise InvalidToken("", csrfToken, securityCookie)
            else:
                print(error)
                print(request.text)
                raise UnknownError(error, "grabConversations")

        if request.json() == []:
            return conversations

# async def createConversation(user, securityCookie, csrfToken):
    # while True:
        # try:
            # async with httpx.AsyncClient() as client:
            # request = await client.post("http://chat.roblox.com/v2/start-one-to-one-conversation", params={"participantUserId": int(user)}, headers={"Cookie": securityCookie, "X-CSRF-TOKEN": csrfToken})
        # except Exception as error:
            # raise UnknownError(error, "createConversation")

        # try:
            # reqJson = request.json()
            # print(reqJson)
            # return reqJson["conversation"]["id"]
        # except Exception as error:
            # if request.status_code == 429:
            # continue
            # print(request.status_code)
            # raise UnknownError(error, "createConversation")


async def sendMessage(conversationID, securityCookie, csrfToken, message, proxy):
    while True:
        try:
            async with httpx.AsyncClient(proxies=proxy) as client:
                request = await client.post("https://chat.roblox.com/v2/send-message", data={"message": message, "conversationId": conversationID}, headers={"Cookie": securityCookie, "X-CSRF-TOKEN": csrfToken})
        except Exception as error:
            raise UnknownError(error, "sendMessage")

        if request.status_code == 200:
            if request.json()["statusMessage"] == "Content was moderated. Message not sent.":
                print('Message was moderated. Trying again.')
            else:
                print(f"Successfully sent message {sent}")
                return
        elif request.status_code == 429:
            continue
        elif request.status_code == 401:
            raise InvalidCookie("", securityCookie)
        elif request.status_code == 403:
            raise InvalidToken("", csrfToken, securityCookie)
        print(request.status_code)
        print(request.text)
        raise UnknownError(
            f"Unknown response code {request.status_code}", "sendMessage")


async def messageFriends(mainQueue, message, updateTask):
    global sent
    global toSend
    while True:
        userDataDict = await mainQueue.get()
        toSend += len(userDataDict["conversations"])
        if userDataDict == None:
            updateTask.cancel()
            return
        print(f"Grabbed {userDataDict['id']}")
        for conversationID in userDataDict["conversations"]:
            try:
                await sendMessage(conversationID, userDataDict["cookie"], userDataDict["token"], message, userDataDict["proxy"])
                sent += 1
                toSend -= 1
            except Exception as error:
                continue


async def updateTitle(mainQueue):
    while True:
        await asyncio.sleep(.25)
        try:
            system(
                "title " + f"Account Queue: {mainQueue.qsize()} - Message Queue: {toSend} - Sent: {sent}")
        except Exception as error:
            print(error)


async def main(loop):
    message = loadMessage()
    global proxyList
    proxyList = loadProxies()
    try:
        cookieQueue = await loadCookies(loop)
    except Exception as error:
        raise(error)

    mainQueue = asyncio.Queue(loop=loop, maxsize=3*int(speed))
    global sent
    global toSend
    sent = 0
    toSend = 0

    tasks = []

    updateTask = asyncio.Task(updateTitle(mainQueue))

    for i in range(int(speed)):
        tasks.append(asyncio.Task(gatherData(mainQueue, cookieQueue)))
        tasks.append(asyncio.Task(messageFriends(
            mainQueue, message, updateTask)))
    tasks.append(updateTask)
    await asyncio.wait(tasks)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(loop))
    loop.close()
    print("All Operations Completed.")
    input("Press enter to exit.")
