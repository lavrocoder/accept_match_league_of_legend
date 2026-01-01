def get_current_queue(queues, queue_id):
    for queue in queues:
        if queue.get("id") == queue_id:
            return queue['name']
    return f"Неизвестный режим ({queue_id})"