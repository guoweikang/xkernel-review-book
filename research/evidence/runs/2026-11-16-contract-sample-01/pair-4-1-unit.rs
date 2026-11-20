fn writeback_cached_folios(
        &self,
        control: &mut WritebackControl,
        mut write_folio_fn: impl FnMut(PageIndex, &[u8], usize) -> VfsResult<()>,
    ) -> VfsResult<()> {
        self.i_pages.writeback_until(
            self.visible_len()?,
            control.range_start()..control.range_end(),
            &mut control.nr_to_write,
            &mut control.pages_skipped,
            &mut write_folio_fn,
        )
    }