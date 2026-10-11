import sys
from pathlib import Path
pp = Path(__file__).resolve().parents[3]
if str(pp) not in sys.path:
    sys.path.insert(0,str(pp))
    

from google import genai
from google.genai.errors import APIError
from AI_Assistent.config.loadenv import API_KEY, AI_MODEL
from AI_Assistent.app.ai.models import AIResponse, SummaryResponse
from AI_Assistent.app.services.saveJsonService import save_json, load_history_from_json
import json
import httpx
import time

historydir = Path(__file__).parents[1] / 'history'
class AiChat():
    def __init__(self, ai_model, response_model, instructions, chatname):
        self.model = ai_model
        self.chatdir = historydir / (chatname + '.json')
        try:
            self.history = load_history_from_json(self.chatdir)
        except json.JSONDecodeError as e:
            print(f'Error {e}. With loading chat history.')
            filelines = Path(historydir / (chatname + '.json'))
            error_line = e.lineno
            start = max(0, error_line - 3)
            end = min(len(filelines), error_line + 2)
            for i in range(start, end):
                print(f'{i + 1}: {filelines[i]}')
        self.history_serialized = []
        if self.history != []:
            for i in self.history:
                message = {}
                message['role'] = i.role
                for p in i.parts:
                    if p.text:
                        message['text'] = p.text
                    if p.file_data:
                        message['file_data'] = {
                            'file_name': p.file_data.file_name,
                            'file_type': p.file_data.file_type
                        }
                self.history_serialized.append(message)
        self.instructions = instructions
        self.config = genai.types.GenerateContentConfig(
            system_instruction=self.instructions,
            response_mime_type='application/json',
            response_schema=response_model,
            max_output_tokens=3000
        )
        self.client = genai.Client(api_key=API_KEY)
        self.chat = self.client.chats.create(
            model=self.model,
            config=self.config,
            history=self.history
        )

    def add_file(self, user_file):
        self.file = self.client.files.upload(file=Path(user_file))

    def save_history(self):
        history = []
        for i in self.chat.get_history()[-2:]:
            self.history.append(i)
        for i in self.history:
            message = {}
            message['role'] = i.role
            text = ''
            filedata = None
            for p in i.parts:
                if p.text:
                    text = p.text
                if p.file_data:
                    if filedata == None:
                        filedata = {}
                    filedata['file_name'] = p.file_data.display_name
                    filedata['file_type'] = p.file_data.mime_type
            message['text'] = text
            message['file_data'] = filedata
            history.append(message)
        self.history_serialized = history
        save_json(self.chatdir, self.history_serialized)

    def summary_history(self):
        summary_config = genai.types.GenerateContentConfig(
            system_instruction='Your task is to summary conversation between AI assitent and the client. You have to tell about what product conversation is, clients intent about its order, clients reason and facts that might be helpful with getting to the couses of whole thing or none in any of that if user did not told anything useful. Try to allow all important informations concise and avoid unimportant informations.',
            response_mime_type='application/json',
            response_schema=SummaryResponse,
            max_output_tokens=500
        )
        summary = self.client.chats.create(
            model='gemini-3.5-flash-lite',
            config=summary_config,
        )
        result = summary.send_message(json.dumps(self.history_serialized, ensure_ascii=False, indent=4)).parsed
        print(result)
        return result

    def new_message(self, content, file):
        summary_used = False
        if self.history != []:
            if self.client.models.count_tokens(model=self.model, contents=self.history).total_tokens > 4000:
                long_story_short = self.summary_history()
                historybutt = self.history
                while self.client.models.count_tokens(model=self.model, contents=historybutt).total_tokens > 1500:
                    historybutt = historybutt[1:]
                if historybutt == []:
                    historybutt = self.history[-1:]
                self.config.system_instruction = self.instructions + '\n\n' + f'Intent established earlier: {long_story_short.intent}. Product established earlier: {long_story_short.product}. Reason established earlier: {long_story_short.reason}. Helpful informations with this client: {long_story_short.helpful_informations}'
                self.chat = self.client.chats.create(
                    model=self.model,
                    config=self.config,
                    history=historybutt
                )
                summary_used = True
        countdown_this_chat = 0
        countdown_new_chat = 0
        while countdown_this_chat < 5 and countdown_new_chat < 5:
            try:
                if file != None:
                    self.add_file(file)
                    print('Sending message')
                    result = self.chat.send_message([content, self.file])
                else:
                    result = self.chat.send_message(content)
                if not result.parsed:
                    print(result)
                    print('Opening new chat')
                    countdown_new_chat += 1
                    if summary_used:
                        self.chat = self.client.chats.create(
                            model=self.model,
                            config=self.config,
                            history=historybutt
                        )
                    else:
                        self.chat = self.client.chats.create(
                            model=self.model,
                            config=self.config,
                            history=self.history
                        )
                else:
                    break
            except (APIError, httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError) as e:
                print(e)
                if isinstance(e, (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError)) or (hasattr(e, 'code') and e.code in [500, 502, 503, 504, 429]):
                    countdown_this_chat += 1
                    print('Retrying with same chat')
                    if hasattr(e, 'code') and e.code == 429:
                        time.sleep(5)
                    continue
                elif hasattr(e, 'code'):
                    print(e.code)
                    match e.code:
                        case 400:
                            return f'Error {e.code} with request.'
                        case 401:
                            return f'Error {e.code} with authentication.'
                        case 402:
                            return f'Error {e.code}. AI service is currently unavilable.'
                        case 403:
                            return f'Error {e.code}. Lack of required permissions.'
                        case 404:
                            return f'Error {e.code}. Requiered resource was not found.'
                        case 501:
                            return f'Error {e.code}. This function is not aviable right now.'
                        case _:
                            return f'Error {e.code}. Unexpected error'
        if countdown_this_chat == 5 or countdown_new_chat == 5:
            return 'This action can not be executed right now. Please try again later.'
        self.save_history()
        print(f'''Tokeny na odpowiedź: {result.usage_metadata.candidates_token_count}
Tokeny na myślenie: {result.usage_metadata.thoughts_token_count}
Łącznie: {result.usage_metadata.candidates_token_count + result.usage_metadata.thoughts_token_count}''')
        return result.parsed
    
aichat = AiChat(AI_MODEL, AIResponse, 'You are client helper chatbot and your task is to tell whether client want to return product, cancel order or check order state. Tell what product client refers to or this field can be null if client does not specified product and the same way fulfill reason', 'chat2')
print(aichat.new_message('Chcę zwrócić anulować zamówienie karty podarunkowej bo je anulowałem przez to że się pokłuciłem z bratankiem o kolor najleprzego napoju i chciałem sprawdzić jego stan to nie pokazywało nic..', Path(historydir / 'chat1.json')))