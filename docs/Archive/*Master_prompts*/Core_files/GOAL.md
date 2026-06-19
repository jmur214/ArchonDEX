# Start:
Please take your time to review **everything** in **GOAL.txt**. You should read it almost as if it were a prompt I have given you. We are **only** going to be doing research and planning at this moment, so just take your time to review the information in the file. 
Importantly, before making any assumptions, or even creating/updating any documentation, you are going to ask me as many clarifying questions as possible/needed to ensure you thoroughly understand our goals and plans stemming from this document. If things seem confusing, or contradictory, you are going to ask me about it. 

**Your Workflow:** First you will understand and thoroughly review the project as detailed below, then you will explore the documents I provide, then you will give me insights into how we should best proceed, before finally asking me any clarifying questions you may have.  


**Below Section's General Outline:** I will first explain to you the big picture of what our machine does and my goals/things I want from it (However, you can and will learn even more about this in the files as detailed below), next I will explain the project origins and what caused this machines inception, after that I will very briefly describe the evolution of the project, following this I will discuss my concerns with the machine and current state of it's documentation and workflow, after this I will present your main task you are going to be working on right now, followed by this I will discuss some of the documents I think would be helpful for our task, finally I will provide you with the documents you are to review. 

 

# Overall Main Goal(s) of this machine for context: 
### Big Picture
We want a professional grade system that eventually learns and trades on it's own. We want to back test enough so that it learns, but not too much that we overfit the machine. It should continue to learn and improve as time goes on from live data based on how well it does/doesn't preform. The main metric for this is win rate, it is crucial that it is above, at minimum 50%, and it should be as close to 100% as possible. The obvious other metric is CAGR for the compound growth, overall profits, and the calmer ratio. Other than that, we can also asses with Sharpe/Sortino ratios, and make sure the max drawdown is not excessive. While these are key metrics, it is by no means exclusive to these alone (just what I can think of off the top of my head). It all should be very realistic to the real world (i.e. no max drawdown >100%, etc.), and overall the main deisire is compounded returns that consistently outperform the market. 

Like I said above, the goal is for the machine to do a combination of sorting through the noise of the market and finding signals, testing if they work, learning what works and what doesn't, compounding our returns while maintaining a well balanced portfolio that significantly outperforms the market. The orginal intent was to have a closed loop system that learned and traded on it's own, that eventually would be able to outperform a human trader as well as the market, and exponentially compounding our returns to unprecedented levels.

You can find out much more about the projects main goals and desires as noted in the below document description section 


### Project origins:
This all came from a combinatation of problems I was having and things that I wanted. The main things were:

A. I had invested into Schwab's Intelligent Portfolio which was like a robo investor but there were quite a few things I didn't like. 
1. It kept at least 10% of my total account in cash, but made the sweep on it for fees.  
2. It invested only in ETFs, I do not mind ETFs and I think they are great, but this also means more consistent returns. 
3. On the same note of ETFs, because of this, even at the very highest risk, it was actually in my mind very low risk. I really wanted to find something that had the possibility, only if I wanted, for really high risk reward opportunities, which wouldn't be done with ETFs only 
4. All of the Schwab ETFs where THEIR own ETFs so they were making money off of me from that as well. 

B. With my dislike for the Schwab Intelligent Portfolio, I still wanted to find a way to passivly make me money in the stock market and have that money compound. The key aspect of this being the compounding, which is one of the most beutiful things in the world and I wanted to be able to really take advantage of this

C. I also wanted to find a way to be able to trade in the stock market, but I didn't want to have to do it myself. I wanted to find a way to have a system that could do it for me, and learn from it, and improve over time. Part of the problem with me trading is I have a bias and am human, and I wanted to mostly remove the human element (while still keeping it there in some instances, not literally, the machine should be autonomous, but it should be able to learn from it's own mistakes and successes and also be able to tell more of a difference than just setting a stop loss and having it get swept out by institutions)

D. I wanted it to learn and continue to learn

E. I wanted it to combine multiple different stratedgies to create some serious alpha, and test those stratedgies to both find the best ones and find when the best time to use them is. The entirety of this, and this is one of the most crucial parts, was to have the machine find "edges" in the market, and execute on those on my behalf, but before executing it would have already tested them to know that it will work on how to best execute.


### V1
The project has evolved a lot over time. The idea originally started out with 3 engines
1. Engine A: Alpha  
2. Engine B: Risk Manager  
3. Engine C: Portfolio Manager

Engine A would find the signals, Engine B would manage the positions, and Engine C would manage the portfolio.  
This morphed into a 4th engine with research or the governor. The goal of this was too find and learn from what was done. Honestly, I am confused about it's difference from A and why we needed to create a new engine but that is besides the point. Engine A & then Engine D are the highlights of what we were aiming to do with the machine that would set it apart from other trading systems. The main thing being FINDING the profitable "edges".  
Finally we have Engine E which seems to do what engine D should be doing. I'm not really sure if we needed a whole new engine for this. The point of the "engines" was to have the most important parts of the system seperated and then the relevant files for the task within each folder

Edges - a large goal of any part of the system is to find "edges" in the market. For me, becuase I don't have super fast data, I called edges anything from a technical edge like moving average crossover to a fundamental edge like what a companies P/E ratio might signal, to news information that might cause movement in a stock, or anything else. My goal was to try and A. find "edges" that worked, and B. combine different edges for the maximum level of success and C. know when different edges work and when they don't so we use better edges at different times. With A, B, and C, the goal was then to learn not only from the past market (without overfitting), but to also learn from it's trading how it could improve, so the machine would just get better and better over time. And another novel aspect of this was to leverage, not just fundamental and technical, but also through it's combination with the news, or even "insider trading" like if nancy pelosi buys X stock we consider buying X stock. 

## Concern that has caused the need for us to improve our documentation
I feel like the project has gotten so big that different parts of the machine are created when they already exist, and we aren't focusing on the highest impact, thus the need to really improve our documentation.  
I feel like the machine has strayed away from our original goals (or at least I can't tell if it has or hasn't), and I want to make sure it stays on track. Personally I didn't keep track of all the updates so I couldn't even show someone how it works, fix any problems, or even really be confident that any tests we do are showing that it works the way it should. When I say "works" I mean it makes money, and will consistently continue to do so. 

I myself and am not sure how to test the machine so that I can be confident in it's ability. I want to go live but I feel as though we are far from ready. 

### What proper functioning would look like: 
>Our machine will A. start paper trading $5000, then B. once we iron out the kinks and make sure it is functioning as best as it can, I will use $5000 of my own money to start trading with it, which is a significant amount of money to me, so we have to be certain it is reliable. Once we are sure it can work like it should and is making me money, I will show others who are willing to invest their own capital. Thus, while we are starting with a low amount, we also need to be able to scale to any amount, (as well as we probably will need to prove it can make money paper trading with significantly larger sums of money) 

# Desires, our goal right now:
We need to figure out a better way to structure how the AI remembers and interacts with the system becuse it has gotten so expansive, and will contine to grow even more. Often it forgets the critical goals of the system as a whole, other times it creates new files that are not needed or we already have some pieces of it elsewhere that just need to be improved. 

Multiple different times we havedone this sort of documentation, but I want to do it once and for all and never have to do it again. We need to clean up the entire docs folder, I'm not really sure whats going on with the different files and folders. I've mostly organized them, but I'm not sure about the accuracy of all of the info in the files and don't want them to create bias. I want this folder to only contain the most crucial documents to best help the AI, the rest should be archieved once we are finished with this process. We aren't going to delete anything, but we are going to create some new files from the ones we have, as well as update some others, and the rest will eventually be archived. We will then have a very clear workflow and set of documents that are easy for an AI or human to understand and follow.  


### Files for our goal right now:

1. The most important starting place for the AI will be this document, **GOAL.md** (we can rename it something else if thats helpful). Once we complete the below, the main purpose of this doc will be to hold the main goal(s) of the entire project in plain english. Both an AI and human will be able to understand it. Much of the information here will be removed or changed, as currently this is not what the final doc will look like. This document will act like a directional prompt, not only highlighting the goals, but also directing it to the below/relevent files. Any time the AI starts losing context, we will refer it back to this document. With this document, any AI could pick up exactly where the last left off. Think of this doc as the orchestrator behind all the other crucual context documents. 

2. We should have **files.txt** just be the files overview. Up until "SUMMARIES" in the document it shows more how this document should function (it likely can be improved, but this is the main goal). After that "SUMMARIES", IT DOES CONTAIN very very helpful information for understanding the system that could be useful elsewhere, for you creating these documents, or understanding the system in general, but this is not the place for that information to be stored. 

3. **!!! This conflicts with what I said in point 1, not sure which approach is better** We should then have a **reminders.md** file, where it says to look at ____ for ____ i.e. this doc (GOAL.txt) for the main goal, files.txt for current files, etc., BUT we should also have it have reminders like - update the readme.md any time we include new commands for a human or AI to run, update files.txt if we create a new one, review X document when forgetting ____, push significant changes to GIT, etc. 

4. We should also have a roadmap with the progress summaries (examples which you will see later). We should create a format for this, and have a reminder to add either a new file for any large upgrade with the date, or just to add new info at the bottom of an ongoing file, whichever you believe is better. Regardless, the roadmap will be constantly updated to keep track of progress, both for humans and AI. Any new significant upgrades, motifications, or fixes should be documented here, every time they are completed. Not while we are working on them, but ONCE they are finished to some degree. 

5. Create a new general best practices file - (not sure if the AIs role should go here or in GOAL.txt)

6. ALSO, should possibly have multiple different AI's/agents with different roles - not sure if we should start new chats for each OR just have like a "system prompt" where I will say "ok now look at ___ file" (the blank is something like roles.md) - **this is a question for you** - but it might have something like "You are a senior architect designing..." or "You are an expert portfolio manager who...", I'm just not sure if it is better to have different roles, or have the AI have 1 giant all encompassing role. This is something to plan together so we will come back to this idea.


**There are likely files that I have left out of the above, so this is not an exlusive list, you are the expert on the topic, and based on my goals, you should know how to best tailor this task. You can and should create any files you think would be most helpful, or revise what I said above.**


## Thoughts for our goal right now
this should be tailored to Google's Antigravity using Gemini, but if we wanted to use another AI like Claude, we could easily tailor it to that as well 

Maybe - for our first prompts/whenever we are chatting with an agent - we need some rule or reminder about how to best attack prompt esp if it's long 

Maybe create a list of "commands" for me the human to give that would trigger an agent or skill or something - like if I just say "GIT" it will do everything (although it would be nice if it could somehow know that we've been working on a problem for a while and to commit once it's actually resolved)

we need tests to verify how things are working  - both literally and functionally 

You should frequently have the AI export its thoughts to a file so it can learn and not repeat mistakes



## Document/folder descriptions:
We have a couple of different files/folders within the docs/ folder. 

*Master_prompts*/ *System_overview*/ and Core_files/ 

*System_overview*/  
- **AI_master.md** is the most recent AI facing prompt, recently before this we had MASTER_CONTEXT.md/MASTER_CONTEXT-v2.md/MASTER_CONTEXT-v3.md which honestly seem like better versions of the AI_master.md just not as recent, and before these we had the file what_to_have_ai_remember.txt - we should maybe have an AI facing context doc, but maybe we don't need this and should instead have specific docs for specific parts of the machine - i.e. files.txt for files, and create other files for similar purposes, we should talk through this idea. Overall, it's ok but has forgotten a lot of the details of the system and our main high level goals. It was created recently so it has been biased.   
- **ARCH_MANIFEST.md** - same issue as above, it is a new file so has some bias, but shows new updates to the machine. 
- **holding.txt** - not sure. no huge value. likely an old roadmap. may provide some insight before our machine has strayed away from it's goals. 
- **system_overview.txt** - 
- **System-Architecture_2.0_Design-Document.txt** - good document as an idea, but I think after this is when we started to veer off course. Good ideas about portfolio management
- **what_to_have_ai_remember.txt** - great doc to show what our original ideas were about the machine, such as edges and importantly the flow of the system 

Core_files/  
- **files.txt** - key file that we will keep adding to, shows in depth the system files and their purposes, etc. the idea here was at first just a quick snapshot of each file, but then we added an overview after that. Realitically, any time we make a new file, we should add it to this file like the other lines that already exist within the file. 
- **files.txt** - overview of files and folders. This is prob the doc that is closest to an overall overview of the project in it's infancy 
- **GOAL.txt** - this file. Once you have read it, and we are done planning, you will update so it just includes the main goals of the project. plain english, high level goals that will always be the same and are number 1 priority. 
- **reminders.txt** - reminders for the AI to always refer to. not yet created, but will be used to store reminders for an AI- **Cognitive Lenses:** `docs/Core/roles.md` outlines specific parameter focuses and mindsets based on the problem at hand (Risk, Quant, UI/UX, etc.) - adopt the corresponding cognitive lens dynamically.
- **README.md** - overview of the project, how to run it, etc. mostly the commands we are able to run (kind of like a man page), and some basic information about the system. 

*Progress_summaries/ 
- **11-9.txt** - great point in time to see the system as it was and some of its feature
- **11-12.txt** - not as good as the above. The above is more a system overview, this is more of a snapshot of a couple of features/changes

Audits/ - all of these files are audits of the system/where the flaws were/what could be fixed. Most of these are newer, so not a lot of good info, but still might show the system currently

Master+Roadmap/ 
- **Master/New/MASTER.md** - the newest master file, it's forgotten a lot of the details of the system and our main high level goals. It was created recently so it has been biased. 
- **Master/Old/** - slightly better than the above, lots of good information, but still not all the best. Regardless, all three files should be reviewed. 

Roadmap/ - just interesting to see where we were going at different points (ROADMAP/ROADMAP-v2/ROADMAP-v3.md were all created at the same time, just like with Master/Old/)

Other/chat_transcripts/

The following files, containing relevant conversations I’ve had with an AI about this machine are to be reviewed. The files and their general contents/importance are as follows (These were conversations had a while ago and their importance was assigned a while ago as well, so things may have been updated since then, regardless they contain **very** helpful information for you to understand the roots of the system)
- **chat1.txt**
    - The starting point to the system development, significant in length, but fundamental to understand the starting point of the system design and how it progressed
- **chat2.txt**
    - A prompt given that then output a somewhat indepth overview of the machine as a whole at that point, used for continuity and reference
- **chat3.txt**
    - Discussion of how trades move markets and how we could incorporate this aspect into paper trading to make it more realistic. Not super important, just for one of the ideas of something we want to include. 
- **chat4.txt**
    - Not important, just some other options of what tech we could use
- **chat5.txt**
    - Very mildly important, just discussion of how to make portfolio more like a “portfolio”
- **chat6.txt**
    - Chat with previous agent reviewing machine as it was, some helpful additions to take into consideration but generally not super important
- **chat7.txt**
    - Same as chat6.txt
- **chat8.txt**
    - Not super important but definitely interesting research backed stratedgies to keep in mind for future development 
- **chat9.txt**
    - Very helpful continuity and context file, this was done when we needed to use another AI as the chat length had ran out and we tried to give it as much context as possible at the time, very helpful
- **chat10.txt**
    - Very very important especially all of the information before the text “North Star” as this is fundamental to the edge discovery/research aspect of the machine and one aspect that definitely needs to be kept in mind 
- **chat11.txt**
    - Unimportant, generally ignore
- **chat12.txt**
    - Very helpful as well as it gives lots of system overview/context/improvements 
Of the above 12 chat(number).txt files, the most critical and crucial for an review in-depth would be 1, 9, 10, 12

Other/credits/ - these contain three different documents from sources detailing some info for how to improve the machine from a trading perspective

Specs/ - I honestly don't know what to call these but you had created these recently. Not super helpful




# EOF - start review other documents 