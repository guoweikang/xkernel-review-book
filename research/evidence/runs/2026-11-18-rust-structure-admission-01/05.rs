fn sample() { let closure = || later(); let future = async { pending(); }; fn local() { nested(); } now(); }
