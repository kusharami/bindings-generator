#for namespace_name in $current_class.namespace_list
namespace ${namespace_name} {
#end for
#set ClassName = $current_class.qtscript_class_name
#set has_base_parent = $current_class.has_base_parent
#if $has_base_parent
	#set ParentClassName = $current_class.base_parent.qtscript_class_name
#else
	#set native_object_type = $current_class.class_name
	#if not $current_class.is_inplace_class
		#set $native_object_type += ' *'
	#end if
	#set ParentClassName = 'QtScriptBaseClassPrototype<{}, {}>'.format($native_object_type, 'true' if $current_class.is_destructor_private else 'false')
#end if
${ClassName}::${ClassName}(QScriptEngine *engine, const QByteArray &className)
	: ${ParentClassName}(engine, className)
{
}

${ClassName}::${ClassName}(QScriptEngine *engine)
	: ${ClassName}(engine, "${current_class.target_class_name}")
{
}

void ${ClassName}::Register(const QScriptValue &targetNamespace)
{
#set static_methods = $current_class.static_methods_clean()
#if $has_base_parent or $static_methods
	auto engine = targetNamespace.engine();
	Q_ASSERT(engine);
#end if	
#if $has_base_parent
	auto inherit = engine->defaultPrototype(qMetaTypeId<${current_class.base_parent.class_name} *>());
#else
	QScriptValue inherit;
#end if
	auto ctor = RegisterT<${current_class.class_name}, ${ClassName}>(targetNamespace, inherit);
	Q_ASSERT(ctor.isFunction());
#for m in $static_methods:
	ctor.setProperty("${m['name']}", engine->newFunction(
		static_cast<QScriptValue (*)(QScriptContext *, QScriptEngine *)>(
			&${ClassName}::${m['name']})),
			QScriptValue::ReadOnly | QScriptValue::Undeletable);
#end for
}

#if $current_class.constructor is None:
int ${ClassName}::constructorArgumentCountMin() const
{
	return 0;
}

int ${ClassName}::constructorArgumentCountMax() const
{
	return 0;
}

bool ${ClassName}::constructObject(QScriptContext *context, NativeObjectType &out)
{
	#if $current_class.is_default_constructable
	if (context->argumentCount() == 0)
	{
		#if not $current_class.is_inplace_class
		out = new ${current_class.class_name};
		#else
		Q_UNUSED(out);
		#end if
		return true;
	}

	QtScriptUtils::badArgumentsException(context,
		"${current_class.namespaced_class_name} constructor");
	#else
	Q_UNUSED(out);
	QtScriptUtils::noPublicConstructorException(context,
		"${current_class.namespaced_class_name}");
	#end if
	return false;
}

#end if