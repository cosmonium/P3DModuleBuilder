
set(PROJECT_NAME CACHE STRING "Module")

cmake_minimum_required (VERSION 3.18)
project (${PROJECT_NAME})

include (FindPackageHandleStandardArgs)

# Project configuration
set(CMAKE_BUILD_TYPE "Release")

if(UNIX AND NOT APPLE)
  set(LINUX TRUE)
endif()

if(LINUX)
  #set(CMAKE_LINK_WHAT_YOU_USE FALSE)
  # TODO: The config above does not work, Why ?
  set(CMAKE_MODULE_LINKER_FLAGS "-Wl,--as-needed")
endif()

# Libraries and options set by the module builder
set(HAVE_LIB_EIGEN CACHE BOOL TRUE)
set(HAVE_LIB_BULLET CACHE BOOL FALSE)
set(HAVE_LIB_FREETYPE CACHE BOOL FALSE)
set(OPTIMIZE CACHE STRING "3")
set(IGATE_VERBOSE CACHE STRING "0")
set(PYTHON_EXECUTABLE CACHE STRING "python")
set(THIRDPARTY_WIN_DIR CACHE STRING "")
set(USE_SDK_PATH CACHE BOOL TRUE)


# --- User controllable variables ---

# Whether to enable SSE. This only has effect on 32 bit.
# Should probably match the setting for the Panda3D build
set(ENABLE_SSE2 CACHE BOOL 1)
set(TOUCHINPUT_ENABLED CACHE BOOL 0)

set(CXX_STANDARD CACHE STRING "14")

# Try Panda3D own find_package(Panda3D) CMake package before falling back
# to the manual SDK detection below.
option(USE_PANDA3D_CMAKE_PACKAGE "Try find_package(Panda3D) before falling back to manual SDK detection" ON)

# --- End of user variables --

# Reset cmake flags - we user our own
set(CMAKE_CXX_FLAGS_RELWITHDEBINFO "")
set(CMAKE_CXX_FLAGS_RELEASE "")
set(CMAKE_CXX_FLAGS_MINSIZEREL "")


set(LIBRARIES "")

# Create the module target up-front, without sources: the actual source
# list is only known once interrogate has generated its wrapper files.
# Creating the target now lets the rest of this file attach
# include directories, definitions and link libraries directly to it with
# target_* commands instead of the whole-directory add_definitions() and
# include_directories() commands.
if (${CMAKE_SYSTEM_NAME} MATCHES "Darwin")
  # macOS won't let us link a .so with another .so, so make a .dylib
  add_library(${PROJECT_NAME} SHARED)
  # Python doesn't detect .dylibs, so rename it .so
  set(CMAKE_SHARED_LIBRARY_SUFFIX ".so")
else()
  add_library(${PROJECT_NAME} MODULE)
endif()

# Don't add lib prefix on Linux
set_target_properties(${PROJECT_NAME} PROPERTIES PREFIX "")

# Locate the Panda3D that is used by the python interpreter
# Empty if it can not be determined.
set(PANDA_PY_INCLUDE_DIR "")
set(PANDA_PY_LIB_DIR "")
if (NOT WIN32)
  foreach (_what include lib)
    execute_process(
      COMMAND "${PYTHON_EXECUTABLE}" "-B" "scripts/common.py" "--print-${_what}-path"
      OUTPUT_VARIABLE _path
      RESULT_VARIABLE _result
      ERROR_QUIET
      OUTPUT_STRIP_TRAILING_WHITESPACE
      WORKING_DIRECTORY ${CMAKE_CURRENT_LIST_DIR})
    if (_result EQUAL 0 AND IS_DIRECTORY "${_path}")
      string(TOUPPER ${_what} _what_upper)
      set(PANDA_PY_${_what_upper}_DIR "${_path}")
    endif()
  endforeach()
  unset(_what)
  unset(_what_upper)
  unset(_path)
  unset(_result)
endif()

# Try Panda3D's own CMake package first.
set(PANDA3D_CMAKE_PACKAGE_FOUND FALSE)
if (USE_PANDA3D_CMAKE_PACKAGE)
  set(_p3d_components Core)
  if (HAVE_LIB_BULLET)
    list(APPEND _p3d_components Bullet)
  endif()
  if (PANDA_PY_LIB_DIR)
    # Find the package of the Panda3D used by python, not the system wise.
    find_package(Panda3D QUIET COMPONENTS ${_p3d_components}
                 HINTS "${PANDA_PY_LIB_DIR}" "${PANDA_PY_LIB_DIR}/.." NO_DEFAULT_PATH)
  else()
    find_package(Panda3D QUIET COMPONENTS ${_p3d_components})
  endif()
  unset(_p3d_components)
  if (Panda3D_FOUND)
    set(PANDA3D_CMAKE_PACKAGE_FOUND TRUE)
    message(STATUS "Found Panda3D via find_package(Panda3D); using its imported targets instead of manual SDK detection")
  endif()
endif()

# Windows - 32 and 64 bit
if (WIN32)
  if (CMAKE_CL_64 STREQUAL "1")
    message(STATUS "Bitness: 64 bit ('${CMAKE_CL_64}')")
    set(IS_64_BIT TRUE)
    set(IS_32_BIT FALSE)
  else()
    message(STATUS "Bitness: 32 bit ('${CMAKE_CL_64}')")
    set(IS_64_BIT TRUE)
    set(IS_32_BIT FALSE)
  endif()

  set(PYTHONVER CACHE STRING "27")

  # Find panda path
  execute_process(
    COMMAND "${PYTHON_EXECUTABLE}" "-B" "scripts/common.py" "--print-sdk-path"
    OUTPUT_VARIABLE WIN_PANDA_PATH
    WORKING_DIRECTORY ${CMAKE_CURRENT_LIST_DIR})
  message(STATUS "Detected panda3d installation: ${WIN_PANDA_PATH}")


  # Determine bitness
  set(THIRDPARTY_SUFFIX "-x64")
  if (IS_32_BIT)
    set(THIRDPARTY_SUFFIX "")
  endif()



  # Find visual studio version
  if (MSVC10)
    set(MSVC_VERSION_SHORT "vc10")
  elseif (MSVC12)
    set(MSVC_VERSION_SHORT "vc12")
  elseif(MSVC14)
    set(MSVC_VERSION_SHORT "vc14")
  else()
    message(WARNING "Unable to determine visual studio version, assuming Visual Studio 2015")
    set(MSVC_VERSION_SHORT "vc14")
  endif()
  message(STATUS "Detected visual studio version: ${MSVC_VERSION_SHORT}")


  set(THIRDPARTY_DIR ${THIRDPARTY_WIN_DIR})
  message(STATUS "Detected thirdparty directory: ${THIRDPARTY_DIR}")

  set(PYTHON_LIBRARIES "${WIN_PANDA_PATH}/python/libs/python${PYTHONVER}.lib")
  set(PYTHON_INCLUDE_DIRS "${WIN_PANDA_PATH}/python/include")
  if (NOT EXISTS "${PYTHON_LIBRARIES}")
    # Panda3D SDK does not ship the requested Python version
    # Find the Python include directories from the Python interpreter used to launch the build script.
    if (PYTHON_EXECUTABLE)
      set(Python3_EXECUTABLE "${PYTHON_EXECUTABLE}")
    endif()
    find_package(Python3 REQUIRED COMPONENTS Interpreter Development.Module)
    set(PYTHON_LIBRARIES "${Python3_LIBRARIES}")
    set(PYTHON_INCLUDE_DIRS "${Python3_INCLUDE_DIRS}")
    message(STATUS "Python executable: ${Python3_EXECUTABLE} (${Python3_VERSION})")
    message(STATUS "Python headers: ${PYTHON_INCLUDE_DIRS}")
    message(STATUS "Python library: ${PYTHON_LIBRARIES}")
  endif()

  if (NOT PANDA3D_CMAKE_PACKAGE_FOUND)
    # Find lib and include directory
    set(PANDA_LIBRARY_DIRS "${WIN_PANDA_PATH}/lib")
    set(PANDA_INCLUDE_DIR "${WIN_PANDA_PATH}/include")

    if (NOT (EXISTS "${PANDA_LIBRARY_DIRS}"))
      message(WARNING "Panda3D library directory does not exist! Expected it at: ${PANDA_LIBRARY_DIRS}")
    endif()
  endif()

  # [LIB] Bullet
  if(HAVE_LIB_BULLET)

    if (NOT (EXISTS "${PANDA_INCLUDE_DIR}/bullet_includes.h"))
      message(FATAL_ERROR "This module requires the bullet library, but your Panda3D Build was compiled without bullet support! Use --use-bullet when compiling.")
    endif()

    target_include_directories(${PROJECT_NAME} PRIVATE "${THIRDPARTY_DIR}/bullet/include/")
    target_link_directories(${PROJECT_NAME} PRIVATE "${THIRDPARTY_DIR}/bullet/lib/")

    if(EXISTS "${THIRDPARTY_DIR}/bullet/lib/LinearMath_x64.lib")
      set(LIBRARIES "${LIBRARIES};LinearMath_x64;BulletCollision_x64;BulletDynamics_x64;BulletSoftBody_x64")
    else()
      set(LIBRARIES "${LIBRARIES};LinearMath;BulletCollision;BulletDynamics;BulletSoftBody")
    endif()
  endif()

  # [LIB] Eigen 3
  if (HAVE_LIB_EIGEN)
    target_include_directories(${PROJECT_NAME} PRIVATE "${THIRDPARTY_DIR}/eigen/include")

    # Eigen build flags (sync with Panda)
    if (HAVE_LIB_EIGEN)
      target_compile_definitions(${PROJECT_NAME} PRIVATE "EIGEN_MPL2_ONLY=")
      if ((OPTIMIZE STREQUAL "3") OR (OPTIMIZE STREQUAL "4"))
        target_compile_definitions(${PROJECT_NAME} PRIVATE "EIGEN_NO_DEBUG=")
        if (MSVC)
          # Squeeze out a bit more performance on MSVC builds...
          # Only do this if EIGEN_NO_DEBUG is also set, otherwise it
          # will turn them into runtime assertions.
          target_compile_definitions(${PROJECT_NAME} PRIVATE "EIGEN_NO_STATIC_ASSERT=")
        endif()
      endif()
    endif()
  endif()

  # [LIB] Freetype
  if (HAVE_LIB_FREETYPE)
    target_include_directories(${PROJECT_NAME} PRIVATE "${THIRDPARTY_DIR}/freetype/include")
    target_include_directories(${PROJECT_NAME} PRIVATE "${THIRDPARTY_DIR}/freetype/include/freetype2")
    target_link_directories(${PROJECT_NAME} PRIVATE "${THIRDPARTY_DIR}/freetype/lib")
    set(LIBRARIES "${LIBRARIES};freetype")
  endif()

  if (NOT PANDA3D_CMAKE_PACKAGE_FOUND)
    # Check if all supplied files exist
    set(CHECK_PATHS ${PANDA_LIBRARY_DIRS} ${PANDA_INCLUDE_DIR} ${PYTHON_LIBRARIES} ${PYTHON_INCLUDE_DIRS})
    foreach(PATH ${CHECK_PATHS})
      if(NOT (EXISTS "${PATH}"))
          message(FATAL_ERROR "The supplied path '${PATH}' could not be found!")
      endif()
    endforeach()

    # Link panda libraries
    set(PANDA_LIBRARIES "libpanda;libpandaexpress;libp3dtool;libp3dtoolconfig;libp3direct")
    # Add interrogate library if shipped with the SDK
    if(EXISTS "${PANDA_LIBRARY_DIRS}/libp3interrogatedb.lib")
      set(PANDA_LIBRARIES "${PANDA_LIBRARIES};libp3interrogatedb")
    endif()
    if(HAVE_LIB_BULLET)
      set(PANDA_LIBRARIES "libpandabullet;${PANDA_LIBRARIES}")
    endif()
    target_link_directories(${PROJECT_NAME} PRIVATE "${PANDA_LIBRARY_DIRS}")
  endif()

else()
  # Find the Python include directories from the Python interpreter used to launch the build script.
  # The include directories can be forced with -DPYTHON_INCLUDE_DIRS
  if ("${PYTHON_INCLUDE_DIRS}" STREQUAL "")
    if (PYTHON_EXECUTABLE)
      set(Python3_EXECUTABLE "${PYTHON_EXECUTABLE}")
    endif()
    find_package(Python3 REQUIRED COMPONENTS Interpreter Development.Module)
    set(PYTHON_INCLUDE_DIRS "${Python3_INCLUDE_DIRS}")
    message(STATUS "Python executable: ${Python3_EXECUTABLE} (${Python3_VERSION})")
    message(STATUS "Python headers: ${PYTHON_INCLUDE_DIRS}")
  endif()

  # [LIB] Bullet
  if (HAVE_LIB_BULLET)
    find_package(Bullet REQUIRED)
    target_include_directories(${PROJECT_NAME} PRIVATE ${BULLET_INCLUDE_DIRS})
    set(LIBRARIES "${LIBRARIES};${BULLET_LIBRARIES}")
  endif()

  # [LIB] Eigen 3
  if (HAVE_LIB_EIGEN)
    if (${CMAKE_SYSTEM_NAME} MATCHES "FreeBSD")
      target_include_directories(${PROJECT_NAME} BEFORE PRIVATE "/usr/local/include/eigen3/")
    else()
      target_include_directories(${PROJECT_NAME} BEFORE PRIVATE "/usr/include/eigen3/")
    endif()

    # Eigen build flags (sync with Panda)
    if (HAVE_LIB_EIGEN)
      target_compile_definitions(${PROJECT_NAME} PRIVATE "EIGEN_MPL2_ONLY=")
      if ((OPTIMIZE STREQUAL "3") OR (OPTIMIZE STREQUAL "4"))
        target_compile_definitions(${PROJECT_NAME} PRIVATE "EIGEN_NO_DEBUG=")
      endif()
    endif()
  endif()

  # [LIB] Freetype
  if(HAVE_LIB_FREETYPE)
    find_package(Freetype REQUIRED)
    target_include_directories(${PROJECT_NAME} PRIVATE ${FREETYPE_INCLUDE_DIRS})
    set(LIBRARIES "${LIBRARIES};${FREETYPE_LIBRARIES}")
  endif()

  if (NOT PANDA3D_CMAKE_PACKAGE_FOUND)
    # Locate the Panda3D headers: first in the Panda3D used by python, then system wise.
     if (PANDA_PY_INCLUDE_DIR)
      find_path(PANDA_INCLUDE_DIR dtoolbase.h PATHS "${PANDA_PY_INCLUDE_DIR}" NO_DEFAULT_PATH)
    endif()
    find_path(PANDA_INCLUDE_DIR dtoolbase.h PATH_SUFFIXES panda3d)

    # Locate the Panda3D libraries, same order
    set(REQ_LIBRARIES panda pandaexpress p3dtool p3dtoolconfig)
    if(HAVE_LIB_BULLET)
      set(REQ_LIBRARIES pandabullet ${REQ_LIBRARIES})
    endif()

    set(PANDA_LIBRARIES "")
    foreach (lib ${REQ_LIBRARIES})
      if (PANDA_PY_LIB_DIR)
        find_library(PANDA_LIBRARY_${lib} ${lib} PATHS "${PANDA_PY_LIB_DIR}" NO_DEFAULT_PATH)
      endif()
      find_library(PANDA_LIBRARY_${lib} ${lib} PATH_SUFFIXES panda3d)
      set(PANDA_LIBRARIES "${PANDA_LIBRARIES};${PANDA_LIBRARY_${lib}}")
    endforeach()

    # Detect if the interrogate library exists, and if so, add it to the list of libraries to link against.
    if (PANDA_PY_LIB_DIR)
      find_library(PANDA_LIBRARY_p3interrogatedb p3interrogatedb PATHS "${PANDA_PY_LIB_DIR}" NO_DEFAULT_PATH)
    endif()
    find_library(PANDA_LIBRARY_p3interrogatedb p3interrogatedb PATH_SUFFIXES panda3d)
    if (PANDA_LIBRARY_p3interrogatedb)
      set(PANDA_LIBRARIES "${PANDA_LIBRARIES};${PANDA_LIBRARY_p3interrogatedb}")
    endif()

    find_package_handle_standard_args(Panda DEFAULT_MSG
                                      PANDA_LIBRARIES PANDA_INCLUDE_DIR)
    message(STATUS "Panda3D headers: ${PANDA_INCLUDE_DIR}")
    message(STATUS "Panda3D libraries: ${PANDA_LIBRARIES}")

    if (NOT EXISTS ${PANDA_INCLUDE_DIR})
      # Okay, the standard package handling failed. Try finding a local panda3d installation

      # Find panda path
      execute_process(
        COMMAND "${PYTHON_EXECUTABLE}" "-B" "scripts/common.py" "--print-sdk-path"
        OUTPUT_VARIABLE LOCAL_PANDA_PATH
        WORKING_DIRECTORY ${CMAKE_CURRENT_LIST_DIR})

      if (NOT EXISTS "${LOCAL_PANDA_PATH}/include")
        message(FATAL_ERROR "Could not find system wide panda3d headers, and no local installation was found!")
      endif()

      set(PANDA_INCLUDE_DIR "${LOCAL_PANDA_PATH}/include")

      set(PANDA_LIBRARIES "")
      foreach(lib ${REQ_LIBRARIES})
        find_library(PANDA_LIBRARY_${lib} ${lib} PATHS "${LOCAL_PANDA_PATH}/lib/")
        set(PANDA_LIBRARIES "${PANDA_LIBRARIES};${PANDA_LIBRARY_${lib}}")
      endforeach()

    endif()
  endif()

endif()

# Find core.so/core.pyd path
execute_process(
  COMMAND "${PYTHON_EXECUTABLE}" "-B" "scripts/common.py" "--print-core-path"
  OUTPUT_VARIABLE PANDA_CORE_PATH
  WORKING_DIRECTORY ${CMAKE_CURRENT_LIST_DIR})


# Link panda includes / libraries
if (NOT PANDA3D_CMAKE_PACKAGE_FOUND)
  target_include_directories(${PROJECT_NAME} PRIVATE "${PANDA_INCLUDE_DIR}")
endif()
target_include_directories(${PROJECT_NAME} PRIVATE "${PYTHON_INCLUDE_DIRS}")

# Resolve which libraries/targets to link the module against for Panda3D
# itself, depending on which of the two paths above was used to find it.
if (PANDA3D_CMAKE_PACKAGE_FOUND)
  set(PANDA_LINK_LIBRARIES Panda3D::Core::panda)
  if (HAVE_LIB_BULLET)
    list(APPEND PANDA_LINK_LIBRARIES Panda3D::Bullet::p3bullet)
  endif()
else()
  set(PANDA_LINK_LIBRARIES ${PANDA_LIBRARIES})
endif()

# Run interrogate over the files
execute_process(
    COMMAND "${PYTHON_EXECUTABLE}" "-B" "${CMAKE_CURRENT_LIST_DIR}/scripts/interrogate.py" "${SHORT_PROJECT_NAME}" "${IGATE_VERBOSE}"
    OUTPUT_VARIABLE output
    ERROR_VARIABLE errors
    RESULT_VARIABLE return_code
    WORKING_DIRECTORY "../..")

if (NOT ("${IGATE_VERBOSE}" STREQUAL "0" ))
  message(STATUS "IGATE stdout = ${output}")
  message(STATUS "IGATE stderr = ${errors}")
endif()

if(NOT ("${return_code}" STREQUAL "0"))
    message(FATAL_ERROR "Interrogate failed: ${output} ${errors}")
endif()

# Set compiler flags
if (MSVC)

  # This matches the makepanda options

  if (IS_64_BIT)
    target_compile_options(${PROJECT_NAME} PRIVATE /favor:blend /DWIN64_VC /DWIN64 /bigobj)
  endif()

  target_compile_options(${PROJECT_NAME} PRIVATE /wd4996 /wd4275 /wd4267 /wd4101 /wd4273)

  if (TOUCHINPUT_ENABLED)
    # If touchinput is enabled
    target_compile_definitions(${PROJECT_NAME} PRIVATE "WINVER=0x601")
  else()
    # If touchinput is disabled
    # target_compile_definitions(${PROJECT_NAME} PRIVATE "WINVER=0x501")
  endif()

  if(IS_32_BIT AND ENABLE_SSE2)
    # If SSE is enabled
    target_compile_options(${PROJECT_NAME} PRIVATE /arch:SSE2)
  endif()

  # Different optimization settings
  if (OPTIMIZE STREQUAL "1")
    target_compile_options(${PROJECT_NAME} PRIVATE /MDd /Zi /RTCs /GS)
  elseif(OPTIMIZE STREQUAL "2")
    target_compile_options(${PROJECT_NAME} PRIVATE /MDd /Zi)
  elseif(OPTIMIZE STREQUAL "3")
    target_compile_options(${PROJECT_NAME} PRIVATE /MD /Zi /GS- /O2 /Ob2 /Oi /Ot /fp:fast)
  elseif(OPTIMIZE STREQUAL "4")
    target_compile_options(${PROJECT_NAME} PRIVATE /MD /Zi /GS- /Ox /Ob2 /Oi /Ot /fp:fast /DFORCE_INLINING /DNDEBUG /GL /LTCG)
    target_compile_options(${PROJECT_NAME} PRIVATE /Oy /Zp16)
  else()
    message(FATAL_ERROR "Invalid optimize value! Was: '${OPTIMIZE}'")
  endif()

  target_compile_options(${PROJECT_NAME} PRIVATE /Zm300 /DWIN32_VC /DWIN32)

  # No exceptions
  target_compile_definitions(${PROJECT_NAME} PRIVATE "_HAS_EXCEPTIONS=0")

  # No RTTI
  target_compile_options(${PROJECT_NAME} PRIVATE /GR-)

  # Warning level 3 should be enough
  target_compile_options(${PROJECT_NAME} PRIVATE /W3)

  # Special case for 32 bit
  if(IS_32_BIT)
    target_compile_options(${PROJECT_NAME} PRIVATE /machine:x86)
  endif()

  # Use multi-core compilation
  target_compile_options(${PROJECT_NAME} PRIVATE /MP)
  # target_compile_options(${PROJECT_NAME} PRIVATE /GM-)

  if (CXX_STANDARD STREQUAL "11")
    # MSVC has no /std: switch for C++11; it always builds at least C++14.
  else()
    target_compile_options(${PROJECT_NAME} PRIVATE /std:c++${CXX_STANDARD})
  endif()

else()
  # Silence CMake warning on macOS
  set(CMAKE_MACOSX_RPATH TRUE)
  # Assuming GCC here

  target_compile_options(${PROJECT_NAME} PRIVATE -ftemplate-depth-70 -fPIC -c)

  # On mac
  if (${CMAKE_SYSTEM_NAME} MATCHES "Darwin")
    target_compile_options(${PROJECT_NAME} PRIVATE -Wno-deprecated-declarations)
  endif()

  target_compile_options(${PROJECT_NAME} PRIVATE -pthread)

  # TODO: Make this more robust...
  if (${CMAKE_SYSTEM_NAME} MATCHES "Darwin")
    target_compile_options(${PROJECT_NAME} PRIVATE -std=gnu++${CXX_STANDARD})
  else()
    target_compile_options(${PROJECT_NAME} PRIVATE -std=c++${CXX_STANDARD})
  endif()

  # No exceptions
  target_compile_options(${PROJECT_NAME} PRIVATE -fno-exceptions)

  # Differnt optimization settings
  if (OPTIMIZE STREQUAL "1")
    target_compile_options(${PROJECT_NAME} PRIVATE -ggdb)
    target_compile_definitions(${PROJECT_NAME} PRIVATE "_DEBUG")
  elseif(OPTIMIZE STREQUAL "2")
    target_compile_options(${PROJECT_NAME} PRIVATE -O1)
    target_compile_definitions(${PROJECT_NAME} PRIVATE "_DEBUG")
  elseif(OPTIMIZE STREQUAL "3")
    target_compile_options(${PROJECT_NAME} PRIVATE -O2)
    target_compile_options(${PROJECT_NAME} PRIVATE -ffast-math -fno-finite-math-only -fno-unsafe-math-optimizations)
  elseif(OPTIMIZE STREQUAL "4")
    target_compile_options(${PROJECT_NAME} PRIVATE -O3 -ffast-math -fno-unsafe-math-optimizations -fno-rtti)
    target_compile_definitions(${PROJECT_NAME} PRIVATE "NDEBUG")
  else()
    message(FATAL_ERROR "Invalid optimize value! Was: '${OPTIMIZE}'")
  endif()

endif()

# Define the module name
target_compile_definitions(${PROJECT_NAME} PRIVATE "PB_MODULE=${PROJECT_NAME}")
target_compile_definitions(${PROJECT_NAME} PRIVATE "PB_CFG_MODULE=${PROJECT_NAME}")

# Collect sources for compiling
set(SOURCES_DIR "${CMAKE_BINARY_DIR}/../..")
file(GLOB SOURCES ${SOURCES_DIR}/*.cpp ${SOURCES_DIR}/*.cxx ${SOURCES_DIR}/*.I ${SOURCES_DIR}/*.hpp ${SOURCES_DIR}/*.h ${SOURCES_DIR}/*.cc ${SOURCES_DIR}/*.c)
target_include_directories(${PROJECT_NAME} PRIVATE ${SOURCES_DIR})
set(SOURCES ${SOURCES_H} ${SOURCES})

# Collect subdirs for compiling
file(GLOB POSSIBLE_DIRS RELATIVE ${SOURCES_DIR} ${SOURCES_DIR}/*)
foreach(PDIR ${POSSIBLE_DIRS})
  if ((IS_DIRECTORY ${SOURCES_DIR}/${PDIR}) AND NOT (${PDIR} STREQUAL "build"))
    target_include_directories(${PROJECT_NAME} PRIVATE "${SOURCES_DIR}/${PDIR}")
    file(GLOB SUB_SOURCES ${SOURCES_DIR}/${PDIR}/*.cpp ${SOURCES_DIR}/${PDIR}/*.cxx ${SOURCES_DIR}/${PDIR}/*.I ${SOURCES_DIR}/${PDIR}/*.hpp ${SOURCES_DIR}/${PDIR}/*.h ${SOURCES_DIR}/${PDIR}/*.cc ${SOURCES_DIR}/${PDIR}/*.c)
    set(SOURCES ${SOURCES} ${SUB_SOURCES})
  endif()
endforeach()


if ((EXISTS "${CMAKE_CURRENT_LIST_DIR}/additional_libs.cmake"))
  include("${CMAKE_CURRENT_LIST_DIR}/additional_libs.cmake")
endif()

target_sources(${PROJECT_NAME} PRIVATE ${SOURCES})

# Add the required libraries
target_link_libraries(${PROJECT_NAME} ${PANDA_LINK_LIBRARIES} ${LIBRARIES})

if (WIN32)
  target_link_libraries(${PROJECT_NAME} ${PYTHON_LIBRARIES})
elseif (APPLE)
  # The Python symbols are resolved when the module is loaded by the interpreter
  target_link_options(${PROJECT_NAME} PRIVATE "LINKER:-undefined,dynamic_lookup")
endif()

if(WIN32)
#   # Eventually link core.pyd?
else()
  set(CMAKE_MODULE_LINKER_FLAGS "${CMAKE_MODULE_LINKER_FLAGS} ${PANDA_CORE_PATH}")
endif()

# After building, copy the file to the current directory
add_custom_command(
    TARGET ${PROJECT_NAME}
    POST_BUILD
    COMMAND "${PYTHON_EXECUTABLE}" "-B" "${CMAKE_CURRENT_LIST_DIR}/scripts/finalize.py" "${PROJECT_NAME}")

# Make shared library paths absolute on macOS
if ((NOT PANDA3D_CMAKE_PACKAGE_FOUND) AND (${CMAKE_SYSTEM_NAME} MATCHES "Darwin"))
  execute_process(
    COMMAND "${PYTHON_EXECUTABLE}" "-B" "scripts/common.py" "--print-lib-path"
    OUTPUT_VARIABLE PANDA_LIB_PATH
    WORKING_DIRECTORY ${CMAKE_CURRENT_LIST_DIR})
  execute_process(
    COMMAND "${PYTHON_EXECUTABLE}" "-B" "scripts/common.py" "--print-short-version"
    OUTPUT_VARIABLE PANDA_SHORT_VERSION
    WORKING_DIRECTORY ${CMAKE_CURRENT_LIST_DIR}
  )

  # The libraries of the SDK the module is linked against, including the interrogate
  # library if the SDK ships it
  set(PANDA_FIXUP_LIBRARIES ${REQ_LIBRARIES})
  if (PANDA_LIBRARY_p3interrogatedb)
    list(APPEND PANDA_FIXUP_LIBRARIES p3interrogatedb)
  endif()

  if (USE_SDK_PATH)
    foreach(lib ${PANDA_FIXUP_LIBRARIES})
      add_custom_command(
        TARGET ${PROJECT_NAME}
        POST_BUILD
        COMMAND "install_name_tool" "-change" "@loader_path/../lib/lib${lib}.${PANDA_SHORT_VERSION}.dylib" "${PANDA_LIB_PATH}/lib${lib}.dylib" "${PROJECT_NAME}${CMAKE_SHARED_LIBRARY_SUFFIX}"
        WORKING_DIRECTORY "../..")
    endforeach()
  else()
    foreach(lib ${PANDA_FIXUP_LIBRARIES})
      add_custom_command(
        TARGET ${PROJECT_NAME}
        POST_BUILD
        COMMAND "install_name_tool" "-change" "@loader_path/../lib/lib${lib}.${PANDA_SHORT_VERSION}.dylib" "@loader_path/../Frameworks/lib${lib}.${PANDA_SHORT_VERSION}.dylib" "${PROJECT_NAME}${CMAKE_SHARED_LIBRARY_SUFFIX}"
        WORKING_DIRECTORY "../..")
    endforeach()
  endif()
endif()
