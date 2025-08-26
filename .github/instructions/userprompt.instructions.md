---
applyTo: '**'
---
This is a project for market research and analysis, focusing on user needs and preferences. 

The goal is develop each component one -by one using on-fly demand . Means User will not tell you full picture of their needs and preferences upfront, instead they will provide feedback and requirements incrementally as the project progresses.
The project will be iterative, with each component being developed based on user feedback and evolving requirements.
Copilot will break down user asks into smaller , manageable tasks and prioritize them based on each task dependency and create trackable todo list.Show this

After successfully implementing user ask copilot will review project implemented so far as a whole and understand at deep level what user is trying to achieve and provide only necessary thoughtful suggestions on an improvement or future feature that will add more value add to project .Its user wish to consider these inputs or not .

***MUST DO***Copilot will track each important project ***files*** and its important components (class, function and their characters along with purpose ) in `project_DNA.md` file . 

It is  ***IMPORTANT*** to vist this file everytime to understand project and make informed decisions.

***DO NOT*** assume anything about user requirements or preferences without explicit confirmation.for example if users asks to implement something to fecth data using api , then dont assume the api endpoint or its parameters,instead ask users to provide required details .same goes for every case that can go wrong in future or cause issues.

Tech Stack:
Python 3.13 Already installed but should use venv
Database MongoDB (verify if installed)
frontend  streamlit (for initial development untill backend code finalized by user)