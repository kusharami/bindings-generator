\#include "${out_file}.hpp"
#if $cpp_headers
#for header in $cpp_headers
\#include "${header}"
#end for
#end if

