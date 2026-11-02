# Imagen de producción: SDK para compilar, runtime para correr.
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src

COPY src/SueldosAr.Core/SueldosAr.Core.csproj src/SueldosAr.Core/
COPY src/SueldosAr.Web/SueldosAr.Web.csproj src/SueldosAr.Web/
RUN dotnet restore src/SueldosAr.Web/SueldosAr.Web.csproj

COPY src/ src/
RUN dotnet publish src/SueldosAr.Web/SueldosAr.Web.csproj -c Release -o /app/publish /p:UseAppHost=false

FROM mcr.microsoft.com/dotnet/aspnet:8.0
WORKDIR /app

COPY --from=build /app/publish .

ENV ASPNETCORE_URLS=http://+:8080
ENV DOTNET_EnableDiagnostics=0
EXPOSE 8080

ENTRYPOINT ["dotnet", "SueldosAr.Web.dll"]
