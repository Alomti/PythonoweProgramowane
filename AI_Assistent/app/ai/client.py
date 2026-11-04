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
from AI_Assistent.app.ai.embeddings_RAG import rag_search
import json
import httpx
import time

historydir = Path(__file__).parents[1] / 'history'
corrupted = Path(historydir / 'corrupted')
class AiChat():
    def __init__(self, ai_model, response_model, instructions, chatname):
        self.model = ai_model
        self.chatfile = historydir / (chatname + '.json')
        try:
            self.history = load_history_from_json(self.chatfile)
            # próba naprawy pliku historii gdy coś nie tak
        except json.JSONDecodeError as e:
            try:
                print(f'Error {e}. With loading chat history.')
                Path(historydir / f'{chatname}.json').replace(Path(corrupted / f'{chatname}.json'))
                filetext = Path(corrupted / (chatname + '.json')).read_text(encoding='utf-8')
                filelines = filetext.splitlines()
                error_line = e.lineno
                start = max(0, error_line - 3)
                end = min(len(filelines), error_line + 2)
                for i in range(start, end):
                    print(f'{i + 1}: {filelines[i]}')
                recovered_history = []
                index = 0
                while True:
                    try:
                        if index >= len(filetext):
                            break
                        while filetext[index].isspace():
                            index += 1
                        if index >= len(filetext):
                            break
                        match filetext[index]:
                            case '[':
                                index += 1
                                continue
                            case ',':
                                index += 1
                                continue
                            case ']':
                                break
                        if index >= len(filetext):
                            break
                        part, index = json.JSONDecoder().raw_decode(filetext, index)
                        recovered_history.append(part)
                    except json.JSONDecodeError:
                        break 
                save_json(self.chatfile, recovered_history)
                self.history = load_history_from_json(self.chatfile)
            except UnicodeDecodeError as e:
                print(f'Error {e} with attempt of recover chat data.')
                self.history = []
        except (FileNotFoundError, PermissionError) as e:
            Path(historydir / f'{chatname}.json').replace(Path(corrupted / f'{chatname}.json'))
            print(f'Error {e} when trying to load chat.')
            self.history = []
        except OSError as e:
            Path(historydir / f'{chatname}.json').replace(Path(corrupted / f'{chatname}.json'))
            print(f'Error {e} when trying to load chat.')
            self.history = []
        except Exception as e:
            Path(historydir / f'{chatname}.json').replace(Path(corrupted / f'{chatname}.json'))
            print(f'Unexpected error: {e} with loading history.')
            self.history = []
        # historia zserializowana do obiektów czystego pythona żeby json potrafił na niej robić operacje
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
            max_output_tokens=3000,
            tools=[rag_search]
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
        last_four = self.chat.get_history()[-4:]
        if len(last_four) < 4:
            for i in last_four:
                self.history.append(i)
        else:
            tool_used = False
            for i in last_four:
                for part in i.parts:
                    if part.function_call or part.function_response:
                        tool_used = True
            if tool_used:
                self.history.append(last_four[0])
                self.history.append(last_four[3])
            else:
                self.history.append(last_four[2])
                self.history.append(last_four[3])
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
        save_json(self.chatfile, self.history_serialized)

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
            # podsumowanie historii przy odpowiedniej ilości tokenów w historii
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
    
aichat = AiChat(AI_MODEL, AIResponse, '''You are a customer support assistant for a small or medium-sized company. Your task is to identify the customer's intent, extract relevant information, and provide a helpful response.
Always use the "rag_search" tool to check the company's documentation before responding.
Treat the company's documentation as the complete and authoritative source of its policies and procedures. If a company policy or procedure is not described in the documentation, assume that the company does not offer or support it. Do not invent exceptions or additional procedures.
Follow these rules when filling the response fields:
"intent":
Identify the customer's intent:
- "return" - the customer wants to return a product.
- "cancel_order" - the customer wants to cancel an order.
- "check_status" - the customer wants to check the status of an order or delivery.
- None - the customer's intent cannot be determined or does not match any of the above.
Choose the best matching intent based on the customer's message. Do not force an intent when there is insufficient information.
A request to exchange a product is not the same as a request to return it. Do not classify an exchange request as "return". Since exchange is not a supported intent, return None for such requests.
"product":
Identify the product the customer refers to. Return None if no product is specified or can be reliably identified.
"reason":
Identify the customer's stated reason or motivation. Do not invent a reason. Return None if no reason can be determined.
"response_to_client":
Provide a clear, concise, and helpful response. Use relevant information from the documentation whenever available.
Follow these rules when interpreting the tool result:
- Relevant documentation found: Answer using information supported by the retrieved documents. Do not add unsupported company policies or procedures.
- No relevant documentation found: Try to help using general knowledge, but clearly explain that the answer is not verified against the company's official documentation. Do not present assumptions or general advice as company policy.
- Tool error: Explain that the company's documentation is temporarily unavailable. You may still offer general guidance, but do not claim to have verified the answer or invent company-specific procedures.
If the documentation only partially answers the customer's question, clearly distinguish confirmed information from anything that cannot be verified.
When documentation does not describe a company policy or procedure, do not suggest that the company might offer undocumented exceptions or alternatives.
The assumption that undocumented policies are not offered applies to company policies and procedures. It does not allow you to invent ordinary factual information, such as opening hours, contact details, or order status. If such information is unavailable, clearly state that it could not be verified.
When explaining company procedures, distinguish between what the customer can do, what the company allows, and what the company or its employees must still approve or complete. Never guarantee that an action will be completed merely because the customer is eligible to request it, submits a form, or contacts support. If the documentation states that an action is possible under certain conditions, explain those conditions without promising a specific outcome unless the documentation explicitly guarantees it.
Never invent order details, company policies, procedures, or facts. Never claim that an action has been completed or that an order has a particular status unless reliable information confirms it.
Do not invent specific company resources, website sections, links, contact methods, or procedures. Only recommend a specific resource or contact method if it is described in the documentation. You may provide general suggestions, but clearly present them as suggestions rather than as existing company services or procedures.
"response_supported_by_documentation":
Return True only when all substantive company-specific information in response_to_client is supported by the retrieved documentation and its stated policies.
Under the assumption that the documentation is complete and authoritative, a conclusion that a company policy or procedure is not offered may be considered supported when the documentation provides sufficient information to establish this.
Return False if the documentation was unavailable, no relevant documentation was found, or any substantive company-specific information relies on unverified information.
The fact that rag_search was called successfully does not by itself mean that the response is supported by documentation.''', 'chat1')
print(aichat.new_message('Kupiłem u was buty, ale niestety są za małe. Co mogę zrobić?', None))