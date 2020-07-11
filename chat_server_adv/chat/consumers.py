import asyncio
import json
from django.contrib.auth import get_user_model
from channels.consumer import AsyncConsumer
from channels.db import database_sync_to_async

from .models import Thread, ChatMessage

class ChatConsumer(AsyncConsumer):
    async def websocket_connect(self,event):
        print("Connected", event)

        # Sending a msg to frontend
        other_user = self.scope['url_route']['kwargs']['username']
        me = self.scope['user']

        thread_obj = await self.get_thread(me,other_user)
        self.thread_obj = thread_obj
        chat_room = f"thread_{thread_obj.id}"
        self.chat_room = chat_room
        await self.channel_layer.group_add(
            chat_room,
            self.channel_name
        )

        await self.send({
            "type": "websocket.accept"
        })



    async def websocket_receive(self,event):
        # When a msg is received from webSocket
        print("receive", event)
        # if no text then None
        front_text = event.get('text',None)
        if front_text is not None:
            loaded_dict_data = json.loads(front_text)
            msg = loaded_dict_data.get('message')
            #
            # attaching username with response
            user = self.scope['user']
            username = 'default'
            # Checking authentication of the user
            if user.is_authenticated:
                username = user.username
            #
            # Preparing Response
            myResponse = {
                'message': msg,
                'username': username
            }
            #
            # Saving msg inside the database
            await self.create_chat_message(user, msg)
            # broadcasts the message event to be send
            await self.channel_layer.group_send(
                self.chat_room,
                {
                    "type": "chat_message",
                    "message": json.dumps(myResponse)
                }
            )

        #receive {'type': 'websocket.receive', 'text': '{"message":"abc"}'}

    async def chat_message(self,event):
        print('message', event)
        # sends actual message
        await self.send({
            "type": "websocket.send",
            "text": event['message']
        })

    async def websocket_disconnect(self,event):
        print("disconnected", event)

    @database_sync_to_async
    def get_thread(self, user, other_username):
        return Thread.objects.get_or_new(user, other_username)[0]

    @database_sync_to_async
    def create_chat_message(self, me, msg):
        thread_obj = self.thread_obj
        return ChatMessage.objects.create(thread= thread_obj,user = me,message= msg)