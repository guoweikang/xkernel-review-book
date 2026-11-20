fn derive_user_write(input: TokenStream) -> TokenStream {
    let input = parse_macro_input!(input as DeriveInput);
    let name = &input.ident;
    let (impl_generics, ty_generics, where_clause) = input.generics.split_for_impl();
    let path = match posix_types_private_path() {
        Ok(path) => path,
        Err(error) => return error.to_compile_error().into(),
    };
    quote! {
        unsafe impl #impl_generics #path::__private::UserWriteTrait for #name #ty_generics #where_clause {}
    }
    .into()
}