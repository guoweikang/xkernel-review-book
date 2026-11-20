fn live_super_blocks(&mut self) -> Vec<Arc<SuperBlock>> {
        let mut live = Vec::new();
        self.super_blocks
            .retain(|super_block| match super_block.upgrade() {
                Some(super_block) => {
                    live.push(super_block);
                    true
                }
                None => false,
            });
        live
    }