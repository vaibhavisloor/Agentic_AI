def main():
    from openai import OpenAI
    print("----- WELCOME TO THE BASICS OF AGENTIC AI BRUHH -----")

    openai = OpenAI(
        api_key='randomxyz',
        base_url='http://127.0.0.1:1234/v1'
    )

    messages1 = [
        {'role':'system', 'content':'You are a maths teacher. You must ask simple maths question. Review the answers provided, give feedback and move on to th enetx question.'},
    ]

    messages2 = [
        {'role':'system', 'content':'You are a maths student who is being quizzed by a teacher. Just answer to the current question that is being asked.'},

    ]


    def interact_with_llm(num,messages):
        nonlocal messages1, messages2

        if num == 1:
            main_message = messages1
            secondary_message = messages2
        elif num == 2:
            main_message = messages2
            secondary_message = messages1

        response = openai.chat.completions.create(
            model = 'llama-3.2-1b-instruct',
            messages = main_message
        )

        ai_response = response.choices[0].message.content
        main_message.append(
            {'role':'assistant','content':ai_response}
        )

        secondary_message.append(
             {'role':'user','content':ai_response}
        )

        print(f"LLM{num} replied :{ai_response}\n\n")


    loop = 0
    while loop < 10:
        interact_with_llm(1,messages1)
        interact_with_llm(2,messages2)
        loop+=1



if __name__ == "__main__":
    main()
