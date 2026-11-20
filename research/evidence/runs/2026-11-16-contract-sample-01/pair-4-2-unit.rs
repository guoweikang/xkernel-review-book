fn submit_cached_ranges<'a>(
        &'a self,
        control: &mut WritebackControl,
        max_bytes: usize,
        mut submit: impl FnMut(WritebackBatch<'a>) -> VfsResult<()>,
    ) -> VfsResult<()> {
        self.i_pages.submit_cache_pages(
            self.visible_len()?,
            control.range_start()..control.range_end(),
            &mut control.nr_to_write,
            &mut control.pages_skipped,
            max_bytes,
            &mut submit,
        )
    }