\#pragma once

#if $hpp_headers
#for header in $hpp_headers
\#include "${header}"
#end for
#end if
#for header in $headers
    #set include_header = os.path.basename(header)
    #if $replace_headers.has_key(include_header)
\#include "${replace_headers[include_header]}"
    #else
        #set relative = os.path.relpath(header, $search_path)
        #if not '..' in relative
\#include "${relative.replace(os.path.sep, '/')}"
        #else
\#include "${include_header}"
        #end if
    #end if
#end for
#if $cpp_headers
#for header in $cpp_headers
\#include "${header}"
#end for
#end if

void qtscript_register_all_${prefix}(QScriptEngine *engine);

