fn poll(&self) -> IoEvents {
        let source = self.source.poll();
        let destination = self.destination.poll();
        if destination.contains(IoEvents::ERR) {
            IoEvents::ERR
        } else if source.contains(IoEvents::IN) && destination.contains(IoEvents::OUT) {
            IoEvents::IN | IoEvents::OUT
        } else if source.contains(IoEvents::HUP) && !source.contains(IoEvents::IN) {
            IoEvents::HUP
        } else {
            IoEvents::empty()
        }
    }