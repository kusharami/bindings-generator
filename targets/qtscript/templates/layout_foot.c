static QScriptValue qtscript_${prefix}_get_target_namespace(
	QScriptEngine *engine, std::initializer_list<const char*> ns_list)
{
	auto result = engine->globalObject();
	for (const char* cns : ns_list)
	{
		auto ns = engine->toStringHandle(QLatin1String(cns));
		auto sv = result.property(ns);
		if (!sv.isObject())
		{
			sv = engine->newObject();
			result.setProperty(ns, sv, QScriptValue::ReadOnly | QScriptValue::Undeletable);
		}
		result = sv;
	}
	return result;
}

void qtscript_register_all_${prefix}(QScriptEngine* engine)
{
	QScriptValue targetNamespace;
#set ns_count = min(len($target_ns), len($cpp_ns))
#set current_ns = -1
#for cls in $sorted_classes()
	#if $cls.is_code_generated
		#set i = 0
		#if $ns_count > 0
			#while $i < $ns_count:
				#if $cls.namespace_name_no_suffix == $cpp_ns[$i]
					#break
				#end if
				#set $i += 1
			#end while
			#assert $i < $ns_count
		#end if
		#if $current_ns != $i
			#set $current_ns = $i
	targetNamespace = QtScriptUtils::getTargetNamespace(engine, {
			#for ns in $target_ns[$i].split('.')
		"${ns}",
			#end for
	});
		#end if
	${cls.namespace_name}${cls.qtscript_class_name}::Register(targetNamespace);
	#end if
#end for
}
