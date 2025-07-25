import panel as pn
import autogen
import io
import openai
import os
import time
import asyncio
from autogen import ConversableAgent
import param


# Snippet below changes background color

css = """
body {
    background-color: #f1b825;
    margin: 0;
    padding: 0;
}

.bk-input {
    background-color: white !important;
}
                         
.no-margin {
    margin: 0 !important;
    padding: 0 !important;
}

.code_bg {
    background: rgb(38, 50, 56);
}

                         
"""

# Allows the CSS to be used on the panel widgets
pn.extension(raw_css = [css])

# Global variable to hold the file content outside of the FileUploader class
test = ""

class FileUploader(param.Parameterized):
    file_input = pn.widgets.FileInput(accept='.py', name='Upload .py file')
    file_input.styles = {'background': 'white'}
    file_content = param.String(default="No file uploaded yet")
    uploaded_content = None  # Class-level variable to store content

    def __init__(self, **params):
        super().__init__(**params)
        self.file_input.param.watch(self.upload_file, 'value')

    @param.depends('file_content')
    def view(self):
        '''This function adds line numbers to a file (if one is uploaded) and then
        displays the code in the appropriate panel'''
        
        lines = self.file_content.split('\n')  # Split into lines
        new_code = ""

        print(lines)
        if lines[0] != 'No file uploaded yet':
            for line_index, line in enumerate(lines, start=1):
                new_code += (f"{line_index:<4} {line}\n")
                
        #If there is no file uploaded, do not add line numbers
        else:
            new_code = self.file_content

        print(new_code)
        return pn.pane.Markdown(f"```python\n{new_code}\n```", sizing_mode='stretch_both', css_classes=['no-margin'])

    def upload_file(self, event):
            global test
            FileUploader.uploaded_content = self.file_input.value.decode('utf-8')  # Update the class-level variable
            self.file_content = FileUploader.uploaded_content
            test = FileUploader.uploaded_content
            # Print the file content (for debugging purposes)
            print("\nUploaded file content:\n", self.file_content)

# Create an instance of the FileUploader class
uploader = FileUploader()

#Create a button to send a "Debug this code" message to the chat
debug_button = pn.widgets.Button(name='Debug the uploaded code', button_type='success')

#Function that sends message to chat interface when button is clicked
def send_message(event):
    message = "Debug the uploaded code"
    #pretty_code = f"```python\n{test}\n```"
    # Assuming you have a function or method to send messages to the chat interface
    if test != "":
        #chat_interface.send(message + " " + pretty_code, user="Student", respond=True)
        chat_interface.send(message, user="Student", respond=False) #content, user (recepient of message), 
        chat_interface.send(f"```python\n{test}\n```", user="Student", respond=True)

# Associate it with send_message function
debug_button.param.watch(send_message, 'clicks')

# Create a button to send an "Explain a concept" message to the chat
explain_button = pn.widgets.Button(name='See AI Examples', button_type='primary')

# Create the dropdown menu for programming concepts (includes subcategories)
select = pn.widgets.Select(
    name='Programming Concepts', 
    groups={
        'Input/Output': ['Print Function', 'Get User Input'], 
        'Data Types': ['Strings', 'Integers', 'Floats', 'Formatted Strings'],
        'Mathematical Expressions': ['Add, Subtract, Multiply', 'Division', 'Exponents'],
        'Data Structures': ['Lists', 'Dictionaries'],
        'Branching': ['If/Else Statements', 'Elif Statements'],
        'Loops': ['For Loops', 'While Loops'],
        'Functions': ['Defining Functions', 'Calling Functions', 'Main Function'],
            })

# Make dropdown background white
select.styles = {'background': 'white'}

#Function that sends message to chat interface when button is clicked
def send_concept_message(event):
    #Allow the concepts select drop-down to show up
    message = f"Give me a brief overview of how to use {select.value} in Python"
    # Assuming you have a function or method to send messages to the chat interface
    chat_interface.send(message, user="Student", respond=True)
    
    
# Watch for button click event
explain_button.param.watch(send_concept_message, 'clicks')

# Define the function to open a new browser tab
def open_url(event):
    import webbrowser
    #Test - print to terminal
    print("The selected option is: ", select.value.lower())
    webbrowser.open_new_tab(f'https://milsteam4144.github.io/python.html/{select.value.lower()}.html')

# Create a button and link it to the function
open_url_button = pn.widgets.Button(name='See Instructor Examples', button_type='primary')
open_url_button.on_click(open_url)


# Header for the page (includes image)
jpg_pane = pn.pane.Image('logo.png', width=120, height=80)
header = pn.Row(jpg_pane, pn.pane.Markdown(
    "# VITA: Virtual Interactive Teaching Assistant"), 
    align='center',
    margin=(10, 0, 20, 10))
header.servable()

#Create a button to hide/show the code snippet 
toggle_button = pn.widgets.Button(name="Show/Hide Uploaded Code", button_type="primary")

# Create the row with the buttons and file input
top_row = pn.Row(
    toggle_button, uploader.file_input, debug_button,
    pn.Spacer(sizing_mode='stretch_width',),
    select,
    explain_button,
    open_url_button,
    sizing_mode='stretch_width',
)

# Print the content outside the class and event handlers
# Note: This will only print once when the script is run, and not update with uploads
print("Content of the uploaded file (initially):", uploader.file_content)

# END FILE UPLOAD COLUMN



# CHAT COLUMN

os.environ["AUTOGEN_USE_DOCKER"] = "False"

# Configuration for LM Studio (local) or OpenAI (cloud)
USE_LOCAL_MODEL = os.environ.get("USE_LOCAL_MODEL", "True").lower() == "true"

if USE_LOCAL_MODEL:
    # LM Studio configuration (default local endpoint)
    config_list = [
        {
            'model': os.environ.get("LOCAL_MODEL_NAME", "dolphin-2.1-mistral-7b"),
            'base_url': os.environ.get("LOCAL_MODEL_URL", "http://localhost:1234/v1"),
            'api_key': "lm-studio",  # LM Studio doesn't require a real API key
        }
    ]
else:
    # OpenAI configuration
    config_list = [
        {
            'model': 'gpt-4o',
            'api_key': os.environ.get("OPENAI_API_KEY"),
        }
    ]
gpt4_config = {"config_list": config_list, "temperature":0, "seed": 53}

input_future = None

# Create a custom agent class that allows human input
class MyConversableAgent(autogen.ConversableAgent):

    async def a_get_human_input(self, prompt: str) -> str:
        global input_future
        print('<Student Input>')  # or however you wish to display the prompt
        chat_interface.send(prompt, user="System", respond=False)
        # Create a new Future object for this input operation if none exists
        if input_future is None or input_future.done():
            input_future = asyncio.Future()

        # Wait for the callback to set a result on the future
        await input_future

        # Once the result is set, extract the value and reset the future for the next input operation
        input_value = input_future.result()
        input_future = None
        return input_value



user_proxy = MyConversableAgent(
   name="Student",
   is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("exit"),
   system_message="""A human student that is learning to code in Python. Interact with the corrector to discuss the plan to fix any errors in the code. \
    The plan to fix the errors in the code needs to be approved by this admin. 
   """,
   #Only say APPROVED in most cases, and say exit when nothing to be done further. Do not say others.
   code_execution_config=False,
   #default_auto_reply="Approved", 
   human_input_mode="ALWAYS",
   #llm_config=gpt4_config,
)

# This agent is currently not being used in the group_chat. It is for testing.
decider = autogen.AssistantAgent(
    name="Decider",
    human_input_mode="NEVER",
    llm_config=gpt4_config,
    system_message='''Decider. If there is a .py file uploaded with content other than None, send the code to the \
Debugger agent. Otherwise, don't mention anything about the uploaded file or debugging code. \
You determine whether the input from the Student is Python code that should be \
debugged or whether it is a request to explain a programming concept. If the input is a request to explain a \
programming \
concept, it will begin with the text "Give me a brief overview of how to use" and then state a programming concept. \
You should then give a brief overview of how the specified programming concept is used in Python.

''',
)

debugger = autogen.AssistantAgent(
    name="Debugger",
    human_input_mode="NEVER",
    llm_config=gpt4_config,
    system_message='''Debugger. You inspect Python code. You find any syntax errors in the code. \
You explain each error as simply as possible in plain English and what line the error occurs on. \
You don't write code.You never show the corrected code. 
''',
)

corrector = autogen.AssistantAgent(
    name="Corrector",
    human_input_mode="NEVER",
    system_message='''Corrector. Suggest a plan to fix each syntax error. \
    Explain how to correct the error as simply as possible using non-technical jargon. \
    You never show the corrected code. However, you may show an example of similar code. Any code that you \
    provide must not be the corrected code to the code you were given. It can only be examples of the same \
    concept, but must use different content as to not give the student the corrected version of their code.
    Revise the plan based on feedback from Student until Student agrees that the correction has \
    successfully fixed their code. If Student does not agree that the correction is sufficient,
    work with the Student to suggest a different solution.
    ''',
    llm_config=gpt4_config,
)


groupchat = autogen.GroupChat(agents=[user_proxy, debugger, corrector], messages=[], max_round=20)
manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=gpt4_config)

avatar = {user_proxy.name:"👨‍💼", debugger.name:"👩‍💻", corrector.name:"🛠",}

# decider.name:"🐍"


def print_messages(recipient, messages, sender, config):

    print(f"Messages from: {sender.name} sent to: {recipient.name} | num messages: {len(messages)} | message: {messages[-1]}")

    content = messages[-1]['content']

    if all(key in messages[-1] for key in ['name']):
        chat_interface.send(content, user=messages[-1]['name'], avatar=avatar[messages[-1]['name']], respond=False)
    else:
        chat_interface.send(content, user=recipient.name, avatar=avatar[recipient.name], respond=False)
    
    return False, None  # required to ensure the agent communication flow continues


user_proxy.register_reply(
    [autogen.Agent, None],
    reply_func=print_messages, 
    config={"callback": None},
)

'''
decider.register_reply(
    [autogen.Agent, None],
    reply_func=print_messages, 
    config={"callback": None},
) 
'''

debugger.register_reply(
    [autogen.Agent, None],
    reply_func=print_messages, 
    config={"callback": None},
) 
corrector.register_reply(
    [autogen.Agent, None],
    reply_func=print_messages, 
    config={"callback": None},
) 


initiate_chat_task_created = False

async def delayed_initiate_chat(agent, recipient, message):

    # Create global variable that indicates if task has been created
    global initiate_chat_task_created

    # Indicate that the task has been created
    initiate_chat_task_created = True

    # Wait for 2 seconds
    await asyncio.sleep(2)

    # Now initiate the chat
    await agent.a_initiate_chat(recipient, message=message)

async def callback(contents: str, user: str, instance: pn.chat.ChatInterface):
    
    global initiate_chat_task_created
    global input_future

    '''
    if not initiate_chat_task_created and FileUploader.uploaded_content != 'No file uploaded yet':
        asyncio.create_task(delayed_initiate_chat(user_proxy, manager, contents))

    
    elif not initiate_chat_task_created and FileUploader.uploaded_content == 'No file uploaded yet':
        asyncio.create_task(delayed_initiate_chat(user_proxy, manager, contents))
    '''
    if not initiate_chat_task_created:
        asyncio.create_task(delayed_initiate_chat(user_proxy, manager, contents))

    else:
        if input_future and not input_future.done():
            input_future.set_result(contents)
        else:
            print("There is currently no input being awaited.")


chat_interface = pn.chat.ChatInterface(callback=callback,)
chat_interface.send("What would you like to ask VITA?", user="System", respond=False)

chat_column = pn.Column(chat_interface, sizing_mode='stretch_both')
chat_column.styles = {'background': 'black'}

# Works with code_snippet_column to show/hide when using toggle button
file_preview = pn.Row(
uploader.view,
)


# The line below utilizes the hide/show code toggle button
code_snippet_column = pn.Column(file_preview, css_classes=['code_bg'], scroll=True)

# Create the main row with the code snippet and chat interface
main_row = pn.Row(
    code_snippet_column,
     pn.layout.Spacer(width=20),
    chat_column,)


# Create a funtion to hide or show the code snippet
def toggle_pane(event):
    if code_snippet_column.visible:
        code_snippet_column.visible = False
        chat_column.sizing_mode = 'stretch_both'
        toggle_button.name = "Show Code"
    else:
        code_snippet_column.visible = True
        toggle_button.name = "Hide Code"

# Attach the toggle function to the button's click event
toggle_button.on_click(toggle_pane)

# NOT using the code toggle button
# code_snippet_column = pn.Column(toggle_button, uploader.view, scroll=False, sizing_mode='stretch_both', margin=(0, 5, 0, 0))

# Create a layout with two columns
layout = pn.Column(top_row, main_row,)

# Serve the panel
layout.servable()
