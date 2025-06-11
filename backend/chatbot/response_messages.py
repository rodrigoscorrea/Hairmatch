class ResponseMessage():
    HAIRDRESSER_NOT_FOUND=(
        'Opa, não conseguimos encontrar esse profissional na nossa base de dados'
    )

    HOW_CAN_I_HELP_YOU_TODAY = (
        f"Como posso te ajudar hoje?\n\n"
        f"*Digite 1* para encontrar um cabeleireiro com base nas suas preferências.\n\n"
        f"*Digite 2* se você já tem um cabeleireiro em mente.\n\n"
        f"*Digite Pare* a qualquer momento para encerar o seu atendimento."
    )

    I_COLLECTED_ENOUGH_DATA_RECOMMEND = (
        "💡 *Já coletei bastante informação! Digite 'recomendar' quando quiser ver as sugestões.*"
    )

    PROBLEM_WHILE_PROCESSING_OPERATION = (
        "Desculpe, estou com um problema para processar sua solicitação no momento. Tente novamente em alguns instantes."
    )

    RECOMMENDATION_RESTART_CHAT = (
        "Opa! Parece que nossa conversa foi interrompida. Vamos recomeçar. Digite '1' para receber recomendações."
    )

    CHAT_STOPPED = ("Atendimento finalizado. Obrigado por conversar comigo!")

    FIND_SPECIFIC_HAIRDRESSER = "Entendido. Qual o nome do cabeleireiro que você procura?"

    SERVICE_TYPE_SEARCH = "Ótimo! Para começar, me diga: que tipo de serviço você está buscando hoje? (ex: corte, coloração, um tratamento especial...)"

    INVALID_OPTION_MESSAGE = "Opção inválida. Por favor, digite '1' para recomendações ou '2' para buscar um profissional específico."