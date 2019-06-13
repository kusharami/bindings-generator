int ${qtscript_class_name}::constructorArgumentCountMin() const
{
	return ${min_args};
}

int ${qtscript_class_name}::constructorArgumentCountMax() const
{
	return ${max_args};
}

bool ${qtscript_class_name}::constructObject(QScriptContext *context, NativeObjectType &out)
{
#if not $is_overloaded
	#set implementations = [$constructor]
#end if
	auto __e = context->engine();
	Q_UNUSED(__e);
	bool ok = false;
	switch (context->argumentCount())
	{
#set cur_min_args = $min_args
#while $cur_min_args <= $max_args
		case ${cur_min_args}:
		{
	#for impl in $implementations
		#if $cur_min_args < $impl.min_args or $cur_min_args > $impl.max_args
			#continue
		#end if
		#set arg_list = []
		#if $cur_min_args > 0
			#set arg_idx = 0
			#while $arg_idx < $cur_min_args
				#set arg = $impl.arguments[$arg_idx]
				#set arg_name = 'arg' + str($arg_idx)
				#set arg_decl = $arg.to_string($generator)
				#set arg_name_tmp = 'tmp_' + str($arg_idx)
				#if $arg.namespaced_name == 'QScriptValue'
					#set from_qtscript = 'context->argument({})'.format($arg_idx)
				#else
					#set from_qtscript = "qscriptvalue_cast<{}>(context->argument({}))".format($arg_decl, $arg_idx);
				#end if
				#set arg_native = $arg.to_native({
						"generator": $generator,
						"arg": $arg,
						"in_value": $arg_name_tmp,
						"default": $arg_name_tmp
					});
				#if $arg_native == $arg_name_tmp
			auto ${arg_name} = ${from_qtscript};
				#else
			auto ${arg_name_tmp} = ${from_qtscript};
			auto ${arg_name} = ${arg_native};
				#end if
				#set $arg_list += [$arg_name]
				#set $arg_idx += 1
			#end while
		#end if
		#set $arg_list = ", ".join($impl.get_native_call_args_with_list($arg_list));
		#set new = '' if $is_inplace_class else 'new '
			#if $new or $arg_list
			out = ${new}${class_name}(${arg_list});
			#else
			Q_UNUSED(out);
			#end if
			ok = true;
		#break
	#end for
			break;
		}
	#set $cur_min_args += 1
#end while
	}
	
	if (!ok)
	{
		QtScriptUtils::badArgumentsException(context,
			"${namespaced_class_name} constructor");
	}
	return ok;
}

