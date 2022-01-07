# coding: utf-8

import discord
from discord.ext import commands

from discord.http import Route
import zlib
import json



class ui_actions():

    def __init__(self, client:discord.Client):
        self.buff = bytearray()
        self.zl = zlib.decompressobj()
        self._dispatch = client.dispatch
        client.event(self.on_socket_response)
        self.client = client
        self._state = client._get_state()



    async def on_socket_response(self, msg):

        if msg["t"] == "INTERACTION_CREATE" and msg["d"]["type"] == 3:
            if msg["d"]["data"]["component_type"] == 2:
                self._dispatch('raw_button_click', msg["d"])
                self._dispatch('button_click', interaction_button_callback(self.client, msg["d"]))
            elif msg["d"]["data"]["component_type"] == 3:
                self._dispatch('raw_menu_select', msg["d"])
                self._dispatch('menu_select', interaction_menu_callback(self.client, msg["d"]))
            else:
                self._dispatch('raw_intraction_ui_action', msg["d"])

    async def send_with_ui(self,channel, content, *, tts=False, embed=None, nonce=None, allowed_mentions=None, message_reference=None,
    ui=None):
        r = Route('POST', '/channels/{channel_id}/messages', channel_id=channel.id)
        payload = {}

        if content:
            payload['content'] = content

        if tts:
            payload['tts'] = True

        if embed:
            payload['embed'] = embed.to_dict()

        if nonce:
            payload['nonce'] = nonce

        if allowed_mentions:
            payload['allowed_mentions'] = allowed_mentions.to_dict()

        if message_reference:
            payload['message_reference'] = message_reference.to_message_reference_dict()

        if ui:
            payload["components"] = [ui.to_dict()]

        data = await self.client.http.request(r, json=payload)
        return self._state.create_message(channel=channel, data=data)


class interaction_menu:

    def __init__(self, menu_id:str, show_text:str="", minc:int=1, maxc:int=1):
        self.custom_id = menu_id
        self.placeholder = show_text
        self.min_values = minc
        self.max_values = maxc
        self.options = []

    def to_dict(self)->dict:
        send_item:dict = {
            "type":1,
            "components":[
                {
                    "type":3,
                    "custom_id":self.custom_id,
                    "placeholder":self.placeholder,
                    "min_values":self.min_values,
                    "max_values":self.max_values,
                    "options":self.options
                }
            ]
        }
        return send_item
    
    def add_option(self, label:str, value:str, description="", emoji=None, default=False):
        if len(self.options) >= 25:
            raise InteractionUiException("you can set 1~25 options.")
        option = {
            "label":label,
            "value":value
        }
        if description:
            option["description"] = description
        if emoji:
            if isinstance(emoji,str):
                option["emoji"] = {
                    "name":emoji,
                    "id":None
                }
            elif isinstance(emoji, (discord.Emoji, discord.PartialEmoji)):
                option["emoji"] = {
                    "name":emoji.name,
                    "id":emoji.id,
                    "animated":emoji.animated
                }
        if default:
            option["default"] = True
        self.options.append(option)
        


class interaction_buttons:

    def __init__(self):
        self.uis = []

    def to_dict(self)->dict:
        if len([x for x in self.uis if x["type"] == 2]) > 5:
            raise InteractionUiException("you can set buttons only 0~5")
        send_item:dict = {
            "type":1,
            "components":self.uis
        }
        return send_item

    def add_button(self, label , style, emoji = None, disabled:bool=False, url=None, custom_id=None):
        if url and custom_id:
            raise InteractionUiException("it's not allowed to have both url and custom_id")
        elif url:
            button = {
                "type":2,
                "label":label,
                "style":style,
                "disabled":disabled,
                "url":url
            }
            if emoji:
                if isinstance(emoji,str):
                    button["emoji"] = {
                        "name":emoji,
                        "id":None
                    }
                elif isinstance(emoji, (discord.Emoji, discord.PartialEmoji)):
                    button["emoji"] = {
                        "name":emoji.name,
                        "id":emoji.id,
                        "animated":emoji.animated
                    }
            self.uis.append(button)
        else:
            if custom_id in [x.get("custom_id","") for x in self.uis if x["type"] == 2]:
                raise InteractionUiException("custom_id must be unique.")
            button = {
                "type":2,
                "label":label,
                "style":style,
                "disabled":disabled,
                "custom_id":custom_id
            }
            if emoji:
                if isinstance(emoji,str):
                    button["emoji"] = {
                        "name":emoji,
                        "id":None
                    }
                elif isinstance(emoji, (discord.Emoji, discord.PartialEmoji)):
                    button["emoji"] = {
                        "name":emoji.name,
                        "id":emoji.id,
                        "animated":emoji.animated
                    }
            self.uis.append(button)
    
    def remove_button(self, label):
        ui_buttons = [x for x in self.uis if x["type"] == 2 and x.get_("label",None) == label]
        if ui_buttons:
            self.uis.remove(ui_buttons[0])

    
    def get_label(self, cid):
        return [i["label"] for i in self.uis if i.get("custom_id","") == cid][0]


class button_style:
    Primary = 1
    Secondary = 2
    Success = 3
    Danger = 4
    Link = 5

class InteractionUiException(Exception):
    pass

class interaction_base_callback:

    def __init__(self,client,data):

        self._token = data["token"]
        self.channel_id = int(data["message"]["channel_id"])
        self._channel = client.get_channel(int(data["message"]["channel_id"]))

        mpl = data["message"]
        
        if data.get("guild_id",None):
            mpl["guild_id"] = data["guild_id"]
            self.guild_id = int(data["guild_id"])


        self.message = client._get_state().create_message(channel=self._channel,data=mpl)


        if self.message.guild:
            self.clicker_id = int(data["member"]["user"]["id"])
            self.clicker = self.message.guild.get_member(self.clicker_id)
        else:
            self.clicker_id = int(data["user"]["id"])
            self.clicker = client.get_user(self.clicker_id)

        self.application_id = data["application_id"]

        self.interaction_id = data["id"]

        self.client = client


    async def response(self, response_type=6):
        r = Route('POST', '/interactions/{interaction_id}/{interaction_token}/callback', interaction_id=self.interaction_id, interaction_token=self._token)

        payload={
            "type":response_type
        }

        await self.client.http.request(r, json=payload)

    async def edit_with_ui(self, content=None, *,  tts=False, embed=None, nonce=None, allowed_mentions=None, message_reference=None,
    ui=None):
        await self.response(response_type=7)
        
        r = Route('PATCH', '/webhooks/{application_id}/{interaction_token}/messages/@original', application_id=self.application_id, interaction_token=self._token)

        payload = {}

        if content:
            payload['content'] = content

        if tts:
            payload['tts'] = True

        if embed:
            payload['embed'] = embed.to_dict()

        if nonce:
            payload['nonce'] = nonce

        if allowed_mentions:
            payload['allowed_mentions'] = allowed_mentions.to_dict()

        if message_reference:
            payload['message_reference'] = message_reference.to_message_reference_dict()

        if ui:
            payload["components"] = [ui.to_dict()]
        elif ui == []:
            payload["components"] = []


        await self.client.http.request(r, json=payload)

    async def send_response_with_ui(self, content=None, *,  tts=False, embed=None, nonce=None, allowed_mentions=None,
    ui=None,hidden = False):
        r = Route('POST', '/interactions/{interaction_id}/{interaction_token}/callback', interaction_id=self.interaction_id, interaction_token=self._token)

        data = {}

        if content:
            data['content'] = content

        if tts:
            data['tts'] = True

        if embed:
            data['embeds'] = [embed.to_dict()]

        if nonce:
            data['nonce'] = nonce

        if allowed_mentions:
            data['allowed_mentions'] = allowed_mentions.to_dict()

        if ui:
            data["components"] = [ui.to_dict()]

        if hidden:
            data["flags"]=64

        payload={
            "type":4,
            "data":data
        }


        await self.client.http.request(r, json=payload)


class interaction_button_callback(interaction_base_callback):

    def __init__(self,client,data):
        super().__init__(client,data)
        self.custom_id = data["data"]["custom_id"]

class interaction_menu_callback(interaction_base_callback):

    def __init__(self,client,data):
        super().__init__(client,data)

        self.custom_id = data["data"]["custom_id"]
        self.selected_value = data["data"]["values"]
  